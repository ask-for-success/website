from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event

from .access_serializers import (
    AccessOptionsSerializer,
    CurrentAccessSerializer,
    UserAccessAssignmentRequestSerializer,
    UserAccessAssignmentSerializer,
)
from .models import User
from .permissions import CanManageAccessAssignments
from .roles import (
    ADDITIONAL_PERMISSION_CODENAMES,
    ADDITIONAL_PERMISSIONS,
    SYSTEM_ROLE_KEYS,
    SYSTEM_ROLES,
    get_user_direct_permission_codes,
    get_user_permission_codes,
    get_user_role_keys,
)
from .serializers import UserSerializer


def build_current_access(user: User) -> dict:
    return {
        "roles": get_user_role_keys(user),
        "permissions": get_user_permission_codes(user),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def build_access_options() -> dict:
    return {
        "roles": [
            {
                "key": role.key,
                "description": role.description,
                "permissions": list(role.permissions),
            }
            for role in SYSTEM_ROLES
        ],
        "additional_permissions": [
            {
                "key": permission.key,
                "description": permission.description,
                "requires_role": permission.requires_role,
            }
            for permission in ADDITIONAL_PERMISSIONS
        ],
    }


def build_user_access_assignment(user: User) -> dict:
    return {
        "user": UserSerializer(user).data,
        "roles": get_user_role_keys(user),
        "direct_permissions": get_user_direct_permission_codes(user),
        "permissions": get_user_permission_codes(user),
    }


def build_access_audit_state(user: User) -> dict:
    role_keys = set(get_user_role_keys(user))
    direct_permissions = set(get_user_direct_permission_codes(user))
    return {
        "account_administrator_access": "account_administrator" in role_keys,
        "content_manager_access": "content_manager" in role_keys,
        "hr_access": "accounts.manage_hr" in direct_permissions,
    }


def clear_permission_cache(user: User) -> None:
    for attribute in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        if hasattr(user, attribute):
            delattr(user, attribute)


class CurrentAccessView(APIView):
    @extend_schema(
        tags=["Access control"],
        summary="Get the current user's access",
        description=(
            "Returns global system roles and effective system permissions. "
            "Membership and event-specific access are intentionally excluded."
        ),
        responses={
            200: CurrentAccessSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def get(self, request):
        return Response(build_current_access(request.user))


class AccessOptionsView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanManageAccessAssignments,
    )

    @extend_schema(
        tags=["Access control"],
        summary="List assignable access options",
        description=(
            "Lists approved global roles and additional individual permissions. "
            "Requires the accounts.manage_access_assignments permission."
        ),
        responses={
            200: AccessOptionsSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Access-management permission required."),
        },
    )
    def get(self, request):
        return Response(build_access_options())


class UserAccessAssignmentView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanManageAccessAssignments,
    )

    @extend_schema(
        tags=["Access control"],
        summary="Get a user's access assignment",
        description=(
            "Returns managed global roles, individually assigned permissions, "
            "and effective system permissions."
        ),
        responses={
            200: UserAccessAssignmentSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Access-management permission required."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        return Response(build_user_access_assignment(target_user))

    @extend_schema(
        tags=["Access control"],
        summary="Replace a user's managed access",
        description=(
            "Replaces managed global roles and additional permissions. Other "
            "Django groups and permissions are preserved. HR permission requires "
            "the content_manager role. A non-superuser cannot change their own access."
        ),
        request=UserAccessAssignmentRequestSerializer,
        responses={
            200: UserAccessAssignmentSerializer,
            400: OpenApiResponse(description="Invalid access assignment."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Access-management permission required."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def put(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user.id == request.user.id and not request.user.is_superuser:
            return Response(
                {"detail": "You cannot change your own access assignment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserAccessAssignmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_role_keys = serializer.validated_data["roles"]
        requested_permission_keys = serializer.validated_data["permissions"]

        managed_groups = Group.objects.filter(name__in=SYSTEM_ROLE_KEYS)
        requested_groups = Group.objects.filter(name__in=requested_role_keys)
        managed_permissions = Permission.objects.filter(
            content_type__app_label="accounts",
            codename__in=ADDITIONAL_PERMISSION_CODENAMES,
        )
        requested_permission_codenames = [
            permission_key.split(".", 1)[1]
            for permission_key in requested_permission_keys
        ]
        requested_permissions = managed_permissions.filter(
            codename__in=requested_permission_codenames
        )
        previous_state = build_access_audit_state(target_user)

        with transaction.atomic():
            target_user.groups.remove(*managed_groups)
            target_user.groups.add(*requested_groups)
            target_user.user_permissions.remove(*managed_permissions)
            target_user.user_permissions.add(*requested_permissions)

            clear_permission_cache(target_user)
            record_audit_event(
                domain=AuditDomain.ACCESS_CONTROL,
                action=AuditAction.ACCESS_ASSIGNMENT_CHANGED,
                actor=request.user,
                target_type="user",
                target_id=target_user.id,
                operation="access_control:user_access_assignment",
                request_method="PUT",
                request_path=request.path,
                previous_state=previous_state,
                new_state=build_access_audit_state(target_user),
            )

        return Response(build_user_access_assignment(target_user))
