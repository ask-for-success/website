from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .account_management import (
    accept_account_invitation,
    create_content_manager_account,
    create_reactivation_invitation,
    deactivate_account,
)
from .models import AccountInvitationEmailStatus, User
from .roles import (
    SYSTEM_ROLE_KEYS,
    get_user_direct_permission_codes,
    get_user_permission_codes,
    get_user_role_keys,
)


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class ManagedAccountSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    direct_permissions = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "direct_permissions",
            "permissions",
            "last_login",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_roles(self, instance) -> list[str]:
        return get_user_role_keys(instance)

    def get_direct_permissions(self, instance) -> list[str]:
        return get_user_direct_permission_codes(instance)

    def get_permissions(self, instance) -> list[str]:
        return get_user_permission_codes(instance)


class ManagedAccountFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(choices=SYSTEM_ROLE_KEYS, required=False)


class ContentManagerAccountCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=32)
    grant_hr_access = serializers.BooleanField(default=False)

    def validate_email(self, value: str) -> str:
        normalized = User.objects.normalize_email(value).lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("This email is already in use.")
        return normalized

    def validate_phone_number(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("This field may not be blank.")
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return normalized

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return create_content_manager_account(
                created_by=request.user,
                request_path=request.path,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class AccountInvitationResultSerializer(serializers.Serializer):
    account = ManagedAccountSerializer(read_only=True)
    invitation_id = serializers.UUIDField(read_only=True)
    purpose = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    email_delivery_status = serializers.ChoiceField(
        choices=AccountInvitationEmailStatus.choices,
        read_only=True,
    )
    email_sent_at = serializers.DateTimeField(read_only=True, allow_null=True)
    email_error = serializers.CharField(read_only=True, allow_blank=True)
    setup_token = serializers.CharField(
        required=False,
        help_text=(
            "Development-only raw setup token. This field is omitted when "
            "DEBUG is disabled."
        ),
    )


class AccountActionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class AccountDeactivateSerializer(AccountActionReasonSerializer):
    def create(self, validated_data):
        request = self.context["request"]
        try:
            return deactivate_account(
                user_id=self.context["user_id"],
                deactivated_by=request.user,
                request_path=request.path,
                **validated_data,
            )
        except (DjangoValidationError, User.DoesNotExist) as error:
            if isinstance(error, User.DoesNotExist):
                raise serializers.ValidationError(
                    {"account": "This account does not exist."}
                ) from error
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class AccountActivateSerializer(AccountActionReasonSerializer):
    def create(self, validated_data):
        request = self.context["request"]
        try:
            return create_reactivation_invitation(
                user_id=self.context["user_id"],
                created_by=request.user,
                request_path=request.path,
                **validated_data,
            )
        except (DjangoValidationError, User.DoesNotExist) as error:
            if isinstance(error, User.DoesNotExist):
                raise serializers.ValidationError(
                    {"account": "This account does not exist."}
                ) from error
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class AccountInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)
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
            return accept_account_invitation(**validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
