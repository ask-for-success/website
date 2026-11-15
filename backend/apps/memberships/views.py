from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    MembershipInvitationAcceptSerializer,
    MembershipInvitationCreateSerializer,
    MembershipInvitationResultSerializer,
)


class MembershipInvitationCreateView(APIView):
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
