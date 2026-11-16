from django.conf import settings
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageHr, CanViewSensitiveIdentity
from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event
from apps.events.models import EventScanner, PublicationStatus

from .models import (
    MemberAssignment,
    MemberIdentity,
    Membership,
    MembershipStatus,
    OnboardingStatus,
)
from .operations import send_membership_invitation_email
from .serializers import (
    ExistingAccountAdmissionSerializer,
    MemberDepartureSerializer,
    MemberAreaSummarySerializer,
    MemberIdentitySerializer,
    MemberTransferSerializer,
    MembershipDetailSerializer,
    MembershipInvitationAcceptSerializer,
    MembershipInvitationCreateSerializer,
    MembershipInvitationResultSerializer,
    MembershipListSerializer,
    OnboardingStatusUpdateSerializer,
    SelfOnboardingSerializer,
)


class MembershipPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def membership_queryset():
    return Membership.objects.select_related(
        "user",
        "onboarding",
        "identity",
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


def member_area_summary_data(membership):
    scanner_assignments = EventScanner.objects.none()
    can_access_member_features = bool(
        membership
        and membership.status == MembershipStatus.ACTIVE
        and membership.onboarding.status == OnboardingStatus.COMPLETED
    )
    onboarding_required = bool(
        membership
        and membership.status == MembershipStatus.PENDING_ONBOARDING
        and membership.onboarding.status != OnboardingStatus.COMPLETED
    )
    if can_access_member_features:
        scanner_assignments = (
            EventScanner.objects.select_related("event")
            .filter(
                membership=membership,
                is_active=True,
                event__ends_at__gte=timezone.now(),
                event__publication_status__in=(
                    PublicationStatus.DRAFT,
                    PublicationStatus.PUBLISHED,
                ),
            )
            .order_by("event__starts_at", "assigned_at")
        )
    return {
        "membership": membership,
        "onboarding_required": onboarding_required,
        "can_access_member_features": can_access_member_features,
        "active_scanner_assignments": scanner_assignments,
    }


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


class MyMembershipSummaryView(APIView):
    @extend_schema(
        tags=["Memberships"],
        summary="Get the current account's member-area summary",
        description=(
            "Returns the authenticated account's membership, onboarding, safe "
            "assignment history, and active upcoming event-scanner assignments. "
            "onboarding_required tells the frontend to show the mandatory "
            "onboarding action, while can_access_member_features remains false "
            "until onboarding is complete. "
            "Accounts without membership receive a successful response with a "
            "null membership. HR-only fields are excluded."
        ),
        responses={
            200: MemberAreaSummarySerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def get(self, request):
        membership = membership_queryset().filter(user=request.user).first()
        return Response(
            MemberAreaSummarySerializer(
                member_area_summary_data(membership)
            ).data
        )


class MyMembershipOnboardingView(APIView):
    @extend_schema(
        tags=["Memberships"],
        summary="Complete the current member's mandatory onboarding",
        description=(
            "The authenticated accepted member submits their national ID number. "
            "The number is never returned in this response and no identity "
            "document is accepted. Successful validation completes onboarding "
            "and activates membership atomically."
        ),
        request=SelfOnboardingSerializer,
        responses={
            200: MemberAreaSummarySerializer,
            400: OpenApiResponse(description="Invalid onboarding submission."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = SelfOnboardingSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        membership = membership_queryset().get(pk=membership.pk)
        return Response(
            MemberAreaSummarySerializer(
                member_area_summary_data(membership)
            ).data
        )


class MembershipIdentityView(APIView):
    permission_classes = (CanViewSensitiveIdentity,)

    @extend_schema(
        tags=["Memberships"],
        summary="View a member's protected national ID number",
        description=(
            "Returns the complete national ID number only to an HR-authorized "
            "content manager, account administrator, or superuser. Every "
            "successful read is explicitly audited without copying the number "
            "into the audit record."
        ),
        responses={
            200: MemberIdentitySerializer,
            403: OpenApiResponse(
                description="HR or account-administrator access required."
            ),
            404: OpenApiResponse(description="Identity record not found."),
        },
    )
    def get(self, request, membership_id):
        identity = get_object_or_404(
            MemberIdentity.objects.select_related("membership"),
            membership_id=membership_id,
        )
        record_audit_event(
            domain=AuditDomain.MEMBERSHIP,
            action=AuditAction.NATIONAL_ID_VIEWED,
            actor=request.user,
            membership=identity.membership,
            new_state={"national_id_collected": True},
        )
        return Response(MemberIdentitySerializer(identity).data)


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
            "Allows HR to mark onboarding as in progress. Only the authenticated "
            "member can complete onboarding and activate membership through the "
            "self-service onboarding endpoint."
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
            "single-use setup token valid for forty-eight hours, then sends the "
            "secure account-setup link by email. The operation requires a content "
            "manager with HR permission. Email failure is recorded without "
            "rolling back the invitation. The raw token is returned only while "
            "the server is running in development mode."
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
        send_membership_invitation_email(result)
        result.invitation.refresh_from_db()
        response_data = {
            "invitation_id": result.invitation.id,
            "email": result.invitation.user.email,
            "expires_at": result.invitation.expires_at,
            "email_delivery_status": (
                result.invitation.email_delivery_status
            ),
            "email_sent_at": result.invitation.email_sent_at,
            "email_error": result.invitation.email_error,
        }
        if settings.DEBUG:
            response_data["setup_token"] = result.setup_token
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
