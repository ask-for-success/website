from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import CanManageAccounts

from .serializers import AdministrationOverviewSerializer
from .services import build_administration_overview


class AdministrationOverviewView(APIView):
    permission_classes = (CanManageAccounts,)

    @extend_schema(
        tags=["Administration"],
        summary="Get the global administration overview",
        description=(
            "Returns current cross-domain totals and the ten most recent audit "
            "records for the administration dashboard. It never returns private "
            "files, national ID values, credentials, or donor contact details."
        ),
        responses={
            200: AdministrationOverviewSerializer,
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Account-management permission required."),
        },
    )
    def get(self, request):
        data = build_administration_overview()
        return Response(AdministrationOverviewSerializer(data).data)
