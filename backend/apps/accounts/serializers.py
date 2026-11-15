from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .tokens import issue_token_pair


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "created_at",
        )
        read_only_fields = fields


class AuthResponseSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)


class TokenPairSerializer(serializers.Serializer):
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "password",
            "password_confirmation",
        )
        extra_kwargs = {
            "email": {"validators": []},
            "phone_number": {
                "validators": [],
                "required": True,
                "allow_null": False,
                "allow_blank": False,
            },
        }

    def validate_email(self, value: str) -> str:
        value = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_phone_number(self, value: str) -> str:
        value = value.strip()
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value

    def validate(self, data):
        password = data.get("password")
        if password != data.get("password_confirmation"):
            raise serializers.ValidationError(
                {"password_confirmation": "The passwords must match."}
            )

        temporary_user = User(
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone_number=data.get("phone_number", ""),
        )
        try:
            password_validation.validate_password(password, user=temporary_user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": list(error.messages)}
            ) from error

        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirmation")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, data):
        user = authenticate(
            request=self.context.get("request"),
            username=data["email"],
            password=data["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        data["user"] = user
        return data


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(trim_whitespace=False)

    def validate(self, data):
        serializer = TokenRefreshSerializer(data={"refresh": data["refresh_token"]})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as error:
            raise serializers.ValidationError(
                {"refresh_token": "The token is invalid or has already been revoked."}
            ) from error
        data["access_token"] = serializer.validated_data["access"]
        data["new_refresh_token"] = serializer.validated_data.get("refresh")
        return data


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(trim_whitespace=False)

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data["refresh_token"]).blacklist()
        except TokenError as error:
            raise serializers.ValidationError(
                {"refresh_token": "The token is invalid or has already been revoked."}
            ) from error


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number")
        extra_kwargs = {"phone_number": {"validators": []}}

    def validate_phone_number(self, value: str) -> str:
        value = value.strip()
        duplicate = User.objects.filter(phone_number=value).exclude(id=self.instance.id)
        if duplicate.exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "The current password is incorrect."}
            )

        new_password = data["new_password"]
        if new_password != data["new_password_confirmation"]:
            raise serializers.ValidationError(
                {"new_password_confirmation": "The new passwords must match."}
            )

        try:
            password_validation.validate_password(new_password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"new_password": list(error.messages)}
            ) from error

        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=("password", "updated_at"))

        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        return user


def build_auth_response(user: User) -> dict:
    return {
        "user": UserSerializer(user).data,
        **issue_token_pair(user),
    }
