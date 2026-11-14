from rest_framework import serializers

from .roles import (
    ADDITIONAL_PERMISSION_BY_KEY,
    ADDITIONAL_PERMISSION_KEYS,
    CONTENT_MANAGER,
    SYSTEM_ROLE_KEYS,
)
from .serializers import UserSerializer


class CurrentAccessSerializer(serializers.Serializer):
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)
    permissions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)


class RoleDefinitionSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    permissions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )


class AdditionalPermissionDefinitionSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    requires_role = serializers.CharField(read_only=True)


class AccessOptionsSerializer(serializers.Serializer):
    roles = RoleDefinitionSerializer(many=True, read_only=True)
    additional_permissions = AdditionalPermissionDefinitionSerializer(
        many=True,
        read_only=True,
    )


class UserAccessAssignmentRequestSerializer(serializers.Serializer):
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=SYSTEM_ROLE_KEYS),
        allow_empty=True,
    )
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=ADDITIONAL_PERMISSION_KEYS),
        allow_empty=True,
    )

    def validate_roles(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Role keys must be unique.")
        return value

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Permission keys must be unique.")
        return value

    def validate(self, data):
        roles = set(data["roles"])
        permissions = data["permissions"]
        for permission_key in permissions:
            required_role = ADDITIONAL_PERMISSION_BY_KEY[
                permission_key
            ].requires_role
            if required_role not in roles:
                raise serializers.ValidationError(
                    {
                        "permissions": (
                            f"{permission_key} requires the {CONTENT_MANAGER} role."
                        )
                    }
                )
        return data


class UserAccessAssignmentSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)
    direct_permissions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
    permissions = serializers.ListField(
        child=serializers.CharField(),
        read_only=True,
    )
