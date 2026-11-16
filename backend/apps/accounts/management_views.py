from uuid import UUID

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .account_management import send_account_invitation_email
from .management_serializers import (
    AccountActivateSerializer,
    AccountDeactivateSerializer,
    AccountInvitationAcceptSerializer,
    AccountInvitationResultSerializer,
    ContentManagerAccountCreateSerializer,
    ManagedAccountFilterSerializer,
    ManagedAccountSerializer,
)
from .models import User
from .permissions import CanManageAccounts


class ManagedAccountPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def invitation_response_data(result) -> dict:
    invitation = result.invitation
    data = {
        "account": invitation.user,
        "invitation_id": invitation.id,
        "purpose": invitation.purpose,
        "expires_at": invitation.expires_at,
        "email_delivery_status": invitation.email_delivery_status,
        "email_sent_at": invitation.email_sent_at,
        "email_error": invitation.email_error,
    }
    if settings.DEBUG:
        data["setup_token"] = result.setup_token
    return AccountInvitationResultSerializer(data).data


ACCOUNT_FILTER_PARAMETERS = [
    OpenApiParameter(
        "search",
        str,
        description="Search by UUID, email, first name, last name, or phone number.",
    ),
    OpenApiParameter("is_active", bool, description="Filter by account state."),
    OpenApiParameter(
        "role",
        str,
        description="Filter by an exact managed global role key.",
    ),
]


class ManagedAccountListCreateView(generics.ListAPIView):
    permission_classes = (CanManageAccounts,)
    serializer_class = ManagedAccountSerializer
    pagination_class = ManagedAccountPagination

    def get_queryset(self):
        filters = ManagedAccountFilterSerializer(
            data=self.request.query_params.dict()
        )
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        queryset = User.objects.prefetch_related(
            "groups",
            "user_permissions",
        ).order_by("email")
        search = values.get("search", "").strip()
        if search:
            criteria = (
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone_number__icontains=search)
            )
            try:
                criteria |= Q(id=UUID(search))
            except ValueError:
                pass
            queryset = queryset.filter(criteria)
        if "is_active" in values:
            queryset = queryset.filter(is_active=values["is_active"])
        if "role" in values:
            queryset = queryset.filter(groups__name=values["role"])
        return queryset.distinct()

    @extend_schema(
        tags=["Account management"],
        summary="List and search accounts",
        parameters=ACCOUNT_FILTER_PARAMETERS,
        responses={
            200: ManagedAccountSerializer(many=True),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Account-management permission required."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Account management"],
        summary="Create an invited content-manager account",
        description=(
            "Creates an inactive content-manager account, optionally grants HR "
            "permission, and sends a single-use password-setup link. The account "
            "cannot authenticate until the invitation is accepted."
        ),
        request=ContentManagerAccountCreateSerializer,
        responses={
            201: AccountInvitationResultSerializer,
            400: OpenApiResponse(description="Invalid or duplicate account data."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Account-management permission required."),
        },
    )
    def post(self, request):
        serializer = ContentManagerAccountCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        send_account_invitation_email(result)
        result.invitation.refresh_from_db()
        return Response(
            invitation_response_data(result),
            status=status.HTTP_201_CREATED,
        )


class ManagedAccountDetailView(generics.RetrieveAPIView):
    permission_classes = (CanManageAccounts,)
    serializer_class = ManagedAccountSerializer
    queryset = User.objects.prefetch_related("groups", "user_permissions")
    lookup_url_kwarg = "user_id"

    @extend_schema(
        tags=["Account management"],
        summary="Get one managed account",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AccountDeactivateView(APIView):
    permission_classes = (CanManageAccounts,)

    @extend_schema(
        tags=["Account management"],
        summary="Deactivate an account",
        description=(
            "Blocks authentication, revokes refresh tokens, removes all roles and "
            "direct permissions, invalidates the old password, and preserves "
            "business records and audit history. Self-deactivation and superuser "
            "deactivation are rejected."
        ),
        request=AccountDeactivateSerializer,
        responses={
            200: ManagedAccountSerializer,
            400: OpenApiResponse(description="The account cannot be deactivated."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Account-management permission required."),
        },
    )
    def post(self, request, user_id):
        get_object_or_404(User, pk=user_id)
        serializer = AccountDeactivateSerializer(
            data=request.data,
            context={"request": request, "user_id": user_id},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(ManagedAccountSerializer(user).data)


class AccountActivateView(APIView):
    permission_classes = (CanManageAccounts,)

    @extend_schema(
        tags=["Account management"],
        summary="Invite an inactive account to reactivate",
        description=(
            "Sends a new single-use password-setup link. The account remains "
            "inactive until the person accepts the invitation. Previous roles and "
            "permissions are not restored automatically."
        ),
        request=AccountActivateSerializer,
        responses={
            201: AccountInvitationResultSerializer,
            400: OpenApiResponse(description="The account cannot be activated."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Account-management permission required."),
        },
    )
    def post(self, request, user_id):
        get_object_or_404(User, pk=user_id)
        serializer = AccountActivateSerializer(
            data=request.data,
            context={"request": request, "user_id": user_id},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        send_account_invitation_email(result)
        result.invitation.refresh_from_db()
        return Response(
            invitation_response_data(result),
            status=status.HTTP_201_CREATED,
        )


class AccountInvitationAcceptView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Account management"],
        summary="Set up or reactivate an invited account",
        description=(
            "Uses a single-use setup token to set a password and activate the "
            "account. The login email cannot be changed."
        ),
        request=AccountInvitationAcceptSerializer,
        responses={
            204: None,
            400: OpenApiResponse(description="Invalid invitation or password."),
        },
    )
    def post(self, request):
        serializer = AccountInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
from uuid import UUID

