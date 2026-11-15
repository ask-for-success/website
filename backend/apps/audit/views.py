from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from .models import AuditRecord
from .permissions import CanViewAuditLog
from .serializers import AuditRecordFilterSerializer, AuditRecordSerializer


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


class AuditRecordListView(generics.ListAPIView):
    serializer_class = AuditRecordSerializer
    permission_classes = (CanViewAuditLog,)
    pagination_class = AuditRecordPagination

    def get_queryset(self):
        filters = AuditRecordFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data

        queryset = AuditRecord.objects.select_related("actor")
        exact_filters = {
            key: values[key]
            for key in (
                "domain",
                "action",
                "actor_id",
                "application_id",
                "membership_id",
            )
            if key in values
        }
        queryset = queryset.filter(**exact_filters)
        if "created_from" in values:
            queryset = queryset.filter(created_at__gte=values["created_from"])
        if "created_to" in values:
            queryset = queryset.filter(created_at__lte=values["created_to"])
        return queryset

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
