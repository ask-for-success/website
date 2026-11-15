from uuid import UUID

from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageHr, is_hr_manager

from .models import (
    ApplicationStatus,
    OpportunityStatus,
    RecruitmentApplication,
    RecruitmentForm,
)
from .models import RecruitmentOpportunity
from .operations import send_application_status_email
from .pagination import RecruitmentPagination
from .serializers import (
    ApplicationStatusUpdateSerializer,
    ApplicationOfferResponseSerializer,
    CandidateApplicationSerializer,
    RecruitmentApplicationCreateSerializer,
    RecruitmentApplicationDetailSerializer,
    RecruitmentApplicationListSerializer,
    RecruitmentFormSerializer,
    RecruitmentOpportunitySerializer,
)


APPLICATION_FILTER_PARAMETERS = [
    OpenApiParameter(
        name="status",
        type=str,
        enum=ApplicationStatus.values,
        location=OpenApiParameter.QUERY,
        description="Filter by application status.",
    ),
    OpenApiParameter(
        name="opportunity_id",
        type=UUID,
        location=OpenApiParameter.QUERY,
        description="Filter by opportunity UUID.",
    ),
    OpenApiParameter(
        name="department_id",
        type=UUID,
        location=OpenApiParameter.QUERY,
        description="Filter by department UUID.",
    ),
    OpenApiParameter(
        name="position_id",
        type=UUID,
        location=OpenApiParameter.QUERY,
        description="Filter by position UUID.",
    ),
    OpenApiParameter(
        name="search",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Search by applicant name or email.",
    ),
]


def parse_uuid_parameter(request, name):
    raw_value = request.query_params.get(name)
    if not raw_value:
        return None
    try:
        return UUID(raw_value)
    except (TypeError, ValueError) as error:
        raise serializers.ValidationError(
            {name: "This query parameter must be a valid UUID."}
        ) from error


def application_queryset():
    return RecruitmentApplication.objects.select_related(
        "applicant",
        "applicant__membership",
        "decision_by",
        "offer_by",
        "opportunity__form__department",
        "opportunity__form__position",
        "cv",
    ).prefetch_related(
        "answers__question",
        "applicant__membership__assignments",
    )


class RecruitmentFormListCreateView(generics.ListCreateAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = RecruitmentFormSerializer
    pagination_class = None
    queryset = RecruitmentForm.objects.select_related(
        "department",
        "position",
        "created_by",
    ).prefetch_related("questions__options")

    @extend_schema(tags=["Recruitment"], summary="List recruitment forms")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Recruitment"],
        summary="Create a department and position recruitment form",
        responses={
            201: RecruitmentFormSerializer,
            403: OpenApiResponse(description="HR permission required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RecruitmentFormDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = RecruitmentFormSerializer
    lookup_url_kwarg = "form_id"
    queryset = RecruitmentForm.objects.select_related(
        "department",
        "position",
        "created_by",
    ).prefetch_related("questions__options")

    @extend_schema(tags=["Recruitment"], summary="Get a recruitment form")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Recruitment"],
        summary="Update an unlocked recruitment form",
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class RecruitmentOpportunityListCreateView(generics.ListCreateAPIView):
    serializer_class = RecruitmentOpportunitySerializer
    pagination_class = RecruitmentPagination

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)
        return (CanManageHr(),)

    def get_queryset(self):
        queryset = RecruitmentOpportunity.objects.select_related(
            "form__department",
            "form__position",
            "created_by",
        ).prefetch_related("form__questions__options")
        if not is_hr_manager(self.request.user):
            queryset = queryset.filter(status=OpportunityStatus.PUBLISHED)
        return queryset

    @extend_schema(tags=["Recruitment"], summary="List recruitment opportunities")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Recruitment"],
        summary="Create a recruitment opportunity",
        responses={
            201: RecruitmentOpportunitySerializer,
            403: OpenApiResponse(description="HR permission required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RecruitmentOpportunityDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = RecruitmentOpportunitySerializer
    lookup_field = "slug__iexact"
    lookup_url_kwarg = "opportunity_slug"

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)
        return (CanManageHr(),)

    def get_queryset(self):
        queryset = RecruitmentOpportunity.objects.select_related(
            "form__department",
            "form__position",
            "created_by",
        ).prefetch_related("form__questions__options")
        if not is_hr_manager(self.request.user):
            queryset = queryset.filter(status=OpportunityStatus.PUBLISHED)
        return queryset

    @extend_schema(tags=["Recruitment"], summary="Get a recruitment opportunity")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Recruitment"], summary="Update a recruitment opportunity")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class RecruitmentApplicationCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        tags=["Recruitment"],
        summary="Apply to a recruitment opportunity",
        description=(
            "Send a multipart request containing a PDF CV and an answers field. "
            "The answers field is a JSON list of question_id and value objects."
        ),
        request=RecruitmentApplicationCreateSerializer,
        responses={
            201: CandidateApplicationSerializer,
            400: OpenApiResponse(description="Invalid or duplicate application."),
        },
    )
    def post(self, request, opportunity_id):
        opportunity = get_object_or_404(
            RecruitmentOpportunity.objects.select_related(
                "form__department",
                "form__position",
            ).prefetch_related("form__questions__options"),
            pk=opportunity_id,
            status=OpportunityStatus.PUBLISHED,
        )
        serializer = RecruitmentApplicationCreateSerializer(
            data=request.data,
            context={"request": request, "opportunity": opportunity},
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        application = application_queryset().get(pk=application.pk)
        return Response(
            CandidateApplicationSerializer(
                application,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class RecruitmentApplicationListView(generics.ListAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = RecruitmentApplicationListSerializer
    pagination_class = RecruitmentPagination

    def get_queryset(self):
        queryset = application_queryset()
        application_status = self.request.query_params.get("status")
        if application_status:
            if application_status not in ApplicationStatus.values:
                raise serializers.ValidationError(
                    {"status": "This application status is invalid."}
                )
            queryset = queryset.filter(status=application_status)
        opportunity_id = parse_uuid_parameter(self.request, "opportunity_id")
        department_id = parse_uuid_parameter(self.request, "department_id")
        position_id = parse_uuid_parameter(self.request, "position_id")
        if opportunity_id:
            queryset = queryset.filter(opportunity_id=opportunity_id)
        if department_id:
            queryset = queryset.filter(
                opportunity__form__department_id=department_id
            )
        if position_id:
            queryset = queryset.filter(opportunity__form__position_id=position_id)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(applicant__email__icontains=search)
                | Q(applicant__first_name__icontains=search)
                | Q(applicant__last_name__icontains=search)
            )
        return queryset

    @extend_schema(
        tags=["Recruitment"],
        summary="List and filter candidate applications",
        parameters=APPLICATION_FILTER_PARAMETERS,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RecruitmentApplicationDetailView(generics.RetrieveAPIView):
    permission_classes = (CanManageHr,)
    serializer_class = RecruitmentApplicationDetailSerializer
    lookup_url_kwarg = "application_id"
    queryset = application_queryset()

    @extend_schema(
        tags=["Recruitment"],
        summary="Get a candidate application, answers, and CV reference",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class RecruitmentApplicationStatusView(APIView):
    permission_classes = (CanManageHr,)

    @extend_schema(
        tags=["Recruitment"],
        summary="Change an application workflow status",
        description=(
            "HR can review, contact, interview, send an offer, or reject. Sending "
            "an offer emails the candidate but creates no membership. Only the "
            "candidate can accept or decline an outstanding offer."
        ),
        request=ApplicationStatusUpdateSerializer,
        responses={200: RecruitmentApplicationDetailSerializer},
    )
    def patch(self, request, application_id):
        application = get_object_or_404(
            application_queryset(),
            pk=application_id,
        )
        serializer = ApplicationStatusUpdateSerializer(
            data=request.data,
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        send_application_status_email(application)
        application = application_queryset().get(pk=application.pk)
        return Response(
            RecruitmentApplicationDetailSerializer(
                application,
                context={"request": request},
            ).data
        )


class RecruitmentApplicationOfferResponseView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        tags=["Recruitment"],
        summary="Accept or decline the authenticated candidate's offer",
        description=(
            "Only the applicant can respond. Acceptance creates or reactivates "
            "membership when needed and withdraws the applicant's other open "
            "applications. Declining creates no membership and leaves other "
            "applications open."
        ),
        request=ApplicationOfferResponseSerializer,
        responses={
            200: CandidateApplicationSerializer,
            400: OpenApiResponse(description="No outstanding offer."),
            404: OpenApiResponse(description="Application not found."),
        },
    )
    def post(self, request, application_id):
        application = get_object_or_404(
            application_queryset(),
            pk=application_id,
            applicant=request.user,
        )
        serializer = ApplicationOfferResponseSerializer(
            data=request.data,
            context={"request": request, "application": application},
        )
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        send_application_status_email(application)
        application = application_queryset().get(pk=application.pk)
        return Response(
            CandidateApplicationSerializer(
                application,
                context={"request": request},
            ).data
        )


class CandidateApplicationListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CandidateApplicationSerializer
    pagination_class = RecruitmentPagination

    def get_queryset(self):
        return application_queryset().filter(applicant=self.request.user)

    @extend_schema(
        tags=["Recruitment"],
        summary="List the authenticated candidate's applications",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ApplicationCvView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        tags=["Recruitment"],
        summary="View a protected application CV",
        responses={
            200: OpenApiResponse(
                response=bytes,
                description="The private PDF CV.",
            ),
            403: OpenApiResponse(description="Applicant or HR access required."),
            404: OpenApiResponse(description="Application or CV not found."),
        },
    )
    def get(self, request, application_id):
        application = get_object_or_404(
            application_queryset(),
            pk=application_id,
        )
        if application.applicant_id != request.user.id and not is_hr_manager(
            request.user
        ):
            self.permission_denied(
                request,
                message="Only the applicant or an HR manager can view this CV.",
            )
        cv = application.cv
        response = FileResponse(
            cv.file.open("rb"),
            content_type="application/pdf",
            filename=cv.original_filename,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
