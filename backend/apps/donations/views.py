from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.accounts.permissions import IsContentManager

from .models import DonationSubmission
from .operations import send_donation_acknowledgement
from .serializers import (
    DonationSubmissionCreateSerializer,
    DonationSubmissionManagerSerializer,
    DonationSubmissionReceiptSerializer,
)


class DonationSubmissionPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class PublicDonationSubmissionView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DonationSubmissionCreateSerializer

    @extend_schema(
        tags=["Donations"],
        summary="Submit donation interest",
        description=(
            "Creates a donation-interest record using the fixed public form. "
            "The donor must select cash or goods. An acknowledgement email is "
            "attempted immediately, and delivery failure never deletes the record."
        ),
        request=DonationSubmissionCreateSerializer,
        responses={
            201: DonationSubmissionReceiptSerializer,
            400: OpenApiResponse(description="Invalid donation submission."),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        send_donation_acknowledgement(submission)
        return Response(
            DonationSubmissionReceiptSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )


class DonationSubmissionListView(generics.ListAPIView):
    permission_classes = (IsContentManager,)
    serializer_class = DonationSubmissionManagerSerializer
    pagination_class = DonationSubmissionPagination

    def get_queryset(self):
        queryset = DonationSubmission.objects.all()
        donation_type = self.request.query_params.get("donation_type")
        email_status = self.request.query_params.get("email_status")
        search = self.request.query_params.get("search", "").strip()
        if donation_type:
            queryset = queryset.filter(donation_type=donation_type)
        if email_status:
            queryset = queryset.filter(
                acknowledgement_email_status=email_status
            )
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
            )
        return queryset

    @extend_schema(
        tags=["Donations"],
        summary="List donation submissions",
        description=(
            "Returns donor contact data only to content managers. Results can "
            "be filtered by donation type or email-delivery status and searched "
            "by donor name, email, or phone number."
        ),
        parameters=[
            OpenApiParameter(
                name="donation_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by cash or goods.",
            ),
            OpenApiParameter(
                name="email_status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by pending, sent, or failed.",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Search by donor name, email, or phone number.",
            ),
        ],
        responses={
            200: DonationSubmissionManagerSerializer(many=True),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DonationSubmissionDetailView(generics.RetrieveAPIView):
    permission_classes = (IsContentManager,)
    serializer_class = DonationSubmissionManagerSerializer
    queryset = DonationSubmission.objects.all()
    lookup_url_kwarg = "submission_id"

    @extend_schema(
        tags=["Donations"],
        summary="Get a donation submission",
        responses={
            200: DonationSubmissionManagerSerializer,
            403: OpenApiResponse(description="Content manager access required."),
            404: OpenApiResponse(description="Donation submission not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

