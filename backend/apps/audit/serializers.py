from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.roles import get_user_permission_codes, get_user_role_keys

from .models import AuditAction, AuditDomain, AuditRecord


class AuditRecordSerializer(serializers.ModelSerializer):
    actor_id = serializers.UUIDField(read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    actor_full_name = serializers.SerializerMethodField()
    application_id = serializers.UUIDField(read_only=True, allow_null=True)
    membership_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = AuditRecord
        fields = (
            "id",
            "domain",
            "action",
            "actor_id",
            "actor_email",
            "actor_full_name",
            "application_id",
            "membership_id",
            "target_type",
            "target_id",
            "operation",
            "request_method",
            "request_path",
            "previous_state",
            "new_state",
            "reason",
            "created_at",
        )
        read_only_fields = fields

    def get_actor_full_name(self, instance) -> str:
        return f"{instance.actor.first_name} {instance.actor.last_name}".strip()


class AuditRecordFilterSerializer(serializers.Serializer):
    domain = serializers.ChoiceField(choices=AuditDomain.choices, required=False)
    action = serializers.ChoiceField(choices=AuditAction.choices, required=False)
    actor_id = serializers.UUIDField(required=False)
    application_id = serializers.UUIDField(required=False)
    membership_id = serializers.UUIDField(required=False)
    created_from = serializers.DateTimeField(required=False)
    created_to = serializers.DateTimeField(required=False)

    def validate(self, attributes):
        created_from = attributes.get("created_from")
        created_to = attributes.get("created_to")
        if created_from and created_to and created_to < created_from:
            raise serializers.ValidationError(
                {"created_to": "The end time must not precede the start time."}
            )
        return attributes


class AuditActorMembershipSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    position = serializers.CharField(allow_null=True)


class AuditActorSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    membership = serializers.SerializerMethodField()
    audit_record_count = serializers.IntegerField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "roles",
            "permissions",
            "membership",
            "audit_record_count",
            "last_activity_at",
        )
        read_only_fields = fields

    def get_roles(self, instance) -> list[str]:
        return get_user_role_keys(instance)

    def get_permissions(self, instance) -> list[str]:
        return get_user_permission_codes(instance)

    @extend_schema_field(AuditActorMembershipSerializer(allow_null=True))
    def get_membership(self, instance):
        try:
            membership = instance.membership
        except ObjectDoesNotExist:
            return None
        assignment = (
            membership.assignments.filter(ends_at__isnull=True)
            .select_related("department", "position")
            .first()
        )
        return {
            "id": str(membership.id),
            "status": membership.status,
            "department": assignment.department.name if assignment else None,
            "position": assignment.position.name if assignment else None,
        }
