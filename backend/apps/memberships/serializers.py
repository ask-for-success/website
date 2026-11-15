from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.organization.models import Department, Position

from .operations import (
    accept_membership_invitation,
    create_membership_invitation,
)


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class MembershipInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="department",
    )
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.filter(is_active=True),
        source="position",
    )

    def create(self, validated_data):
        try:
            return create_membership_invitation(
                created_by=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class MembershipInvitationResultSerializer(serializers.Serializer):
    invitation_id = serializers.UUIDField()
    email = serializers.EmailField()
    expires_at = serializers.DateTimeField()
    setup_token = serializers.CharField()


class MembershipInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)
    phone_number = serializers.CharField(max_length=32)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "The passwords must match."}
            )
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirmation")
        try:
            return accept_membership_invitation(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
