from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event

from .serializers import (
    AuthResponseSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UpdateProfileSerializer,
    UserSerializer,
    build_auth_response,
)


class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Authentication"],
        summary="Register a user account",
        description=(
            "Creates an ordinary active account without email verification and "
            "returns the user with an access and refresh token pair."
        ),
        request=RegisterSerializer,
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        record_audit_event(
            domain=AuditDomain.ACCOUNTS,
            action=AuditAction.ACCOUNT_REGISTERED,
            actor=user,
            target_type="user",
            target_id=user.id,
            operation="accounts:register",
            request_method="POST",
            request_path=request.path,
        )
        return Response(build_auth_response(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Authentication"],
        summary="Log in with email and password",
        description=(
            "Authenticates an active account using a case-insensitive email "
            "address and returns a token pair."
        ),
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description="Invalid credentials."),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        record_audit_event(
            domain=AuditDomain.ACCOUNTS,
            action=AuditAction.ACCOUNT_LOGIN,
            actor=user,
            target_type="user",
            target_id=user.id,
            operation="accounts:login",
            request_method="POST",
            request_path=request.path,
        )
        return Response(build_auth_response(user))


class RefreshView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh and rotate tokens",
        description=(
            "Returns a new access and refresh token pair and revokes the submitted "
            "refresh token."
        ),
        request=RefreshSerializer,
        responses={
            200: TokenPairSerializer,
            400: OpenApiResponse(description="Invalid or revoked refresh token."),
        },
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_data = {"access_token": serializer.validated_data["access_token"]}
        new_refresh_token = serializer.validated_data["new_refresh_token"]
        if new_refresh_token:
            response_data["refresh_token"] = new_refresh_token
        return Response(response_data)


class LogoutView(APIView):
    @extend_schema(
        tags=["Authentication"],
        summary="Log out",
        description="Revokes the submitted refresh token.",
        request=LogoutSerializer,
        responses={
            204: None,
            400: OpenApiResponse(description="Invalid or revoked refresh token."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    @extend_schema(
        tags=["Authentication"],
        summary="Get the current user",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=["Authentication"],
        summary="Update the current user",
        description="Updates first name, last name, or phone number.",
        request=UpdateProfileSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def patch(self, request):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


class ChangePasswordView(APIView):
    @extend_schema(
        tags=["Authentication"],
        summary="Change the current user's password",
        description=(
            "Changes the password and invalidates all existing access and refresh "
            "tokens for the user."
        ),
        request=ChangePasswordSerializer,
        responses={
            204: None,
            400: OpenApiResponse(description="Password validation error."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
