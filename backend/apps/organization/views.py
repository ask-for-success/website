from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions

from .models import Department, Position
from .serializers import DepartmentSerializer


def active_departments():
    return Department.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            "positions",
            queryset=Position.objects.filter(is_active=True).order_by("name"),
        )
    )


class DepartmentListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DepartmentSerializer
    pagination_class = None

    def get_queryset(self):
        return active_departments()

    @extend_schema(
        tags=["Organization"],
        summary="List active departments and positions",
        description=(
            "Returns reference data used by recruitment, invitations, admissions, "
            "and department transfers."
        ),
        responses={200: DepartmentSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DepartmentDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DepartmentSerializer
    lookup_url_kwarg = "department_id"

    def get_queryset(self):
        return active_departments()

    @extend_schema(
        tags=["Organization"],
        summary="Get an active department and its positions",
        responses={
            200: DepartmentSerializer,
            404: OpenApiResponse(description="Department not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
