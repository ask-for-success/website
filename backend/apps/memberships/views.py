from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageHr

from .models import MemberAssignment, Membership
from .serializers import (
    ExistingAccountAdmissionSerializer,
    MemberDepartureSerializer,
    MemberTransferSerializer,
    MembershipDetailSerializer,
    MembershipInvitationAcceptSerializer,
    MembershipInvitationCreateSerializer,
    MembershipInvitationResultSerializer,
    MembershipListSerializer,
    OnboardingStatusUpdateSerializer,
)


class MembershipPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def membership_queryset():
    return Membership.objects.select_related(
        "user",
        "onboarding",
    ).prefetch_related(
        Prefetch(
            "assignments",
            queryset=MemberAssignment.objects.select_related(
                "department",
                "position",
                "assigned_by",
            ).order_by("-starts_at"),
        )
    )


class MembershipListView(generics.ListAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = MembershipListSerializer
    pagination_class = MembershipPagination

    def get_queryset(self):
        queryset = membership_queryset()
        membership_status = self.request.query_params.get("status")
        department_id = self.request.query_params.get("department_id")
        search = self.request.query_params.get("search", "").strip()
        if membership_status:
            queryset = queryset.filter(status=membership_status)
        if department_id:
            queryset = queryset.filter(
                assignments__department_id=department_id,
                assignments__ends_at__isnull=True,
            )
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )
        return queryset.distinct()

    @extend_schema(
        tags=["Memberships"],
        summary="List memberships",
        description=(
            "Lists membership and onboarding state for authorized HR content "
            "managers. The current assignment is included when one exists."
        ),
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by membership status.",
            ),
            OpenApiParameter(
                name="department_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by current department UUID.",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by member name or email.",
            ),
        ],
        responses={
            200: MembershipListSerializer(many=True),
            403: OpenApiResponse(description="HR permission required."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MembershipDetailView(generics.RetrieveAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = MembershipDetailSerializer
    lookup_url_kwarg = "membership_id"

    def get_queryset(self):
        return membership_queryset()

    @extend_schema(
        tags=["Memberships"],
        summary="Get a membership and assignment history",
        responses={
            200: MembershipDetailSerializer,
            403: OpenApiResponse(description="HR permission required."),
            404: OpenApiResponse(description="Membership not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ExistingAccountAdmissionView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Memberships"],
        summary="Admit an existing account",
        description=(
            "Creates a pending membership, onboarding record, and initial "
            "assignment for an active account that does not have a membership."
        ),
        request=ExistingAccountAdmissionSerializer,
        responses={
            201: MembershipDetailSerializer,
            400: OpenApiResponse(description="Invalid admission."),
            403: OpenApiResponse(description="HR permission required."),
        },
    )
    def post(self, request):
        serializer = ExistingAccountAdmissionSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        membership = membership_queryset().get(pk=membership.pk)
        return Response(
            MembershipDetailSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


class MembershipTransferView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Memberships"],
        summary="Transfer a member",
        description=(
            "Atomically ends the current assignment and creates one assignment "
            "in the new department. Onboarding is not repeated."
        ),
        request=MemberTransferSerializer,
        responses={
            200: MembershipDetailSerializer,
            400: OpenApiResponse(description="Invalid transfer."),
            403: OpenApiResponse(description="HR permission required."),
            404: OpenApiResponse(description="Membership not found."),
        },
    )
    def post(self, request, membership_id):
        membership = get_object_or_404(Membership, pk=membership_id)
        serializer = MemberTransferSerializer(
            data=request.data,
            context={"request": request, "membership": membership},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership = membership_queryset().get(pk=membership.pk)
        return Response(MembershipDetailSerializer(membership).data)


class MembershipOnboardingView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Memberships"],
        summary="Update membership onboarding state",
        description=(
            "Starts or completes onboarding. Completion activates the membership. "
            "Completed onboarding cannot be reopened."
        ),
        request=OnboardingStatusUpdateSerializer,
        responses={
            200: MembershipDetailSerializer,
            400: OpenApiResponse(description="Invalid onboarding transition."),
            403: OpenApiResponse(description="HR permission required."),
            404: OpenApiResponse(description="Membership not found."),
        },
    )
    def patch(self, request, membership_id):
        membership = get_object_or_404(Membership, pk=membership_id)
        serializer = OnboardingStatusUpdateSerializer(
            data=request.data,
            context={"request": request, "membership": membership},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership = membership_queryset().get(pk=membership.pk)
        return Response(MembershipDetailSerializer(membership).data)


class MembershipDepartureView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Memberships"],
        summary="Record a member departure",
        description=(
            "Ends the current assignment, marks the membership inactive, and "
            "preserves the account, onboarding, and assignment history."
        ),
        request=MemberDepartureSerializer,
        responses={
            200: MembershipDetailSerializer,
            400: OpenApiResponse(description="Invalid departure."),
            403: OpenApiResponse(description="HR permission required."),
            404: OpenApiResponse(description="Membership not found."),
        },
    )
    def post(self, request, membership_id):
        membership = get_object_or_404(Membership, pk=membership_id)
        serializer = MemberDepartureSerializer(
            data=request.data,
            context={"request": request, "membership": membership},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        membership = membership_queryset().get(pk=membership.pk)
        return Response(MembershipDetailSerializer(membership).data)


class MembershipInvitationCreateView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Memberships"],
        summary="Invite an already accepted member",
        description=(
            "Creates an inactive account, membership, initial assignment, and "
            "single-use setup token valid for forty-eight hours. The operation "
            "requires a content manager with HR permission. The raw token is "
            "returned once for testing until email delivery is connected."
        ),
        request=MembershipInvitationCreateSerializer,
        responses={
            201: MembershipInvitationResultSerializer,
            400: OpenApiResponse(description="Invalid data."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="HR permission required."),
        },
    )
    def post(self, request):
        serializer = MembershipInvitationCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        response_data = {
            "invitation_id": result.invitation.id,
            "email": result.invitation.user.email,
            "expires_at": result.invitation.expires_at,
            "setup_token": result.setup_token,
        }
        return Response(
            MembershipInvitationResultSerializer(response_data).data,
            status=status.HTTP_201_CREATED,
        )


class MembershipInvitationAcceptView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Memberships"],
        summary="Set up an invited member account",
        description=(
            "Uses the invitation token once to store a phone number and password, "
            "then activates the account. This action does not approve a candidate; "
            "the membership was approved before the invitation was created."
        ),
        request=MembershipInvitationAcceptSerializer,
        responses={
            204: None,
            400: OpenApiResponse(description="Invalid invitation or data."),
        },
    )
    def post(self, request):
        serializer = MembershipInvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
