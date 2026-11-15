from uuid import UUID

from django.db.models import Count, F, Max, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from apps.accounts.models import User

from .models import AuditRecord
from .permissions import CanViewAuditLog
from .serializers import (
    AuditActorSerializer,
    AuditRecordFilterSerializer,
    AuditRecordSerializer,
)


class AuditRecordPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


AUDIT_FILTER_PARAMETERS = [
    OpenApiParameter("domain", str, description="Filter by audit domain."),
    OpenApiParameter("action", str, description="Filter by exact action."),
    OpenApiParameter("actor_id", str, description="Filter by actor UUID."),
    OpenApiParameter(
        "application_id",
        str,
        description="Filter by recruitment application UUID.",
    ),
    OpenApiParameter(
        "membership_id",
        str,
        description="Filter by membership UUID.",
    ),
    OpenApiParameter(
        "created_from",
        str,
        description="Return records created at or after this ISO 8601 time.",
    ),
    OpenApiParameter(
        "created_to",
        str,
        description="Return records created at or before this ISO 8601 time.",
    ),
]


def apply_audit_filters(queryset, query_params, *, include_actor=True):
    filters = AuditRecordFilterSerializer(data=query_params)
    filters.is_valid(raise_exception=True)
    values = filters.validated_data
    exact_filter_keys = [
        "domain",
        "action",
        "application_id",
        "membership_id",
    ]
    if include_actor:
        exact_filter_keys.append("actor_id")
    exact_filters = {
        key: values[key]
        for key in exact_filter_keys
        if key in values
    }
    queryset = queryset.filter(**exact_filters)
    if "created_from" in values:
        queryset = queryset.filter(created_at__gte=values["created_from"])
    if "created_to" in values:
        queryset = queryset.filter(created_at__lte=values["created_to"])
    return queryset


class AuditRecordListView(generics.ListAPIView):
    serializer_class = AuditRecordSerializer
    permission_classes = (CanViewAuditLog,)
    pagination_class = AuditRecordPagination

    def get_queryset(self):
        queryset = AuditRecord.objects.select_related("actor")
        return apply_audit_filters(queryset, self.request.query_params)

    @extend_schema(
        tags=["Audit"],
        summary="List immutable audit records",
        parameters=AUDIT_FILTER_PARAMETERS,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditRecordDetailView(generics.RetrieveAPIView):
    serializer_class = AuditRecordSerializer
    permission_classes = (CanViewAuditLog,)
    queryset = AuditRecord.objects.select_related("actor")
    lookup_url_kwarg = "record_id"

    @extend_schema(tags=["Audit"], summary="Get an immutable audit record")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditActorListView(generics.ListAPIView):
    serializer_class = AuditActorSerializer
    permission_classes = (CanViewAuditLog,)
    pagination_class = AuditRecordPagination

    def get_queryset(self):
        queryset = (
            User.objects.annotate(
                audit_record_count=Count("audit_records"),
                last_activity_at=Max("audit_records__created_at"),
                audit_full_name=Concat(
                    "first_name",
                    Value(" "),
                    "last_name",
                ),
            )
            .prefetch_related("groups", "user_permissions")
            .order_by(F("last_activity_at").desc(nulls_last=True), "email")
        )
        search = self.request.query_params.get("search", "").strip()
        if not search:
            return queryset
        criteria = (
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(audit_full_name__icontains=search)
        )
        try:
            criteria |= Q(id=UUID(search))
        except ValueError:
            pass
        return queryset.filter(criteria)

    @extend_schema(
        tags=["Audit"],
        summary="Search accounts for activity review",
        parameters=[
            OpenApiParameter(
                "search",
                str,
                description="Search by user UUID, email, first name, or full name.",
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditActorRecordListView(generics.ListAPIView):
    serializer_class = AuditRecordSerializer
    permission_classes = (CanViewAuditLog,)
    pagination_class = AuditRecordPagination

    def get_queryset(self):
        actor = get_object_or_404(User, pk=self.kwargs["actor_id"])
        queryset = AuditRecord.objects.select_related("actor").filter(actor=actor)
        return apply_audit_filters(
            queryset,
            self.request.query_params,
            include_actor=False,
        )

    @extend_schema(
        tags=["Audit"],
        summary="List all recorded activity for one account",
        parameters=[
            parameter
            for parameter in AUDIT_FILTER_PARAMETERS
            if parameter.name != "actor_id"
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
