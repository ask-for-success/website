from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.organization.models import Department, Position

from .models import (
    MemberAssignment,
    Membership,
    MembershipOnboarding,
    OnboardingStatus,
)
from .operations import (
    accept_membership_invitation,
    admit_existing_account,
    create_membership_invitation,
    record_member_departure,
    transfer_member,
    update_onboarding_status,
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


class MembershipUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_active",
        )


class DepartmentReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "name")


class PositionReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("id", "name")


class AssignmentActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")


class MemberAssignmentSerializer(serializers.ModelSerializer):
    department = DepartmentReferenceSerializer(read_only=True)
    position = PositionReferenceSerializer(read_only=True)
    assigned_by = AssignmentActorSerializer(read_only=True)

    class Meta:
        model = MemberAssignment
        fields = (
            "id",
            "department",
            "position",
            "assigned_by",
            "starts_at",
            "ends_at",
            "end_reason",
        )


class MembershipOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipOnboarding
        fields = (
            "status",
            "started_at",
            "completed_at",
            "updated_at",
        )


class MembershipListSerializer(serializers.ModelSerializer):
    user = MembershipUserSerializer(read_only=True)
    onboarding = MembershipOnboardingSerializer(read_only=True)
    current_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = (
            "id",
            "user",
            "status",
            "accepted_at",
            "onboarding",
            "current_assignment",
            "updated_at",
        )

    @extend_schema_field(MemberAssignmentSerializer(allow_null=True))
    def get_current_assignment(self, instance):
        assignment = next(
            (
                item
                for item in instance.assignments.all()
                if item.ends_at is None
            ),
            None,
        )
        if assignment is None:
            return None
        return MemberAssignmentSerializer(assignment).data


class MembershipDetailSerializer(MembershipListSerializer):
    assignment_history = serializers.SerializerMethodField()

    class Meta(MembershipListSerializer.Meta):
        fields = MembershipListSerializer.Meta.fields + (
            "assignment_history",
            "created_at",
        )

    @extend_schema_field(MemberAssignmentSerializer(many=True))
    def get_assignment_history(self, instance):
        assignments = [
            item for item in instance.assignments.all() if item.ends_at is not None
        ]
        return MemberAssignmentSerializer(assignments, many=True).data


class MemberAreaAssignmentSerializer(serializers.ModelSerializer):
    department = DepartmentReferenceSerializer(read_only=True)
    position = PositionReferenceSerializer(read_only=True)

    class Meta:
        model = MemberAssignment
        fields = (
            "id",
            "department",
            "position",
            "starts_at",
            "ends_at",
        )
        read_only_fields = fields


class MemberAreaMembershipSerializer(serializers.ModelSerializer):
    onboarding = MembershipOnboardingSerializer(read_only=True)
    current_assignment = serializers.SerializerMethodField()
    assignment_history = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = (
            "id",
            "status",
            "accepted_at",
            "onboarding",
            "current_assignment",
            "assignment_history",
        )
        read_only_fields = fields

    @extend_schema_field(MemberAreaAssignmentSerializer(allow_null=True))
    def get_current_assignment(self, instance):
        assignment = next(
            (
                item
                for item in instance.assignments.all()
                if item.ends_at is None
            ),
            None,
        )
        if assignment is None:
            return None
        return MemberAreaAssignmentSerializer(assignment).data

    @extend_schema_field(MemberAreaAssignmentSerializer(many=True))
    def get_assignment_history(self, instance):
        assignments = [
            item for item in instance.assignments.all() if item.ends_at is not None
        ]
        return MemberAreaAssignmentSerializer(assignments, many=True).data


class MemberAreaEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    summary = serializers.CharField()
    location = serializers.CharField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    requires_qr_code = serializers.BooleanField()


class MemberAreaScannerAssignmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    assigned_at = serializers.DateTimeField()
    event = MemberAreaEventSerializer()


class MemberAreaSummarySerializer(serializers.Serializer):
    membership = MemberAreaMembershipSerializer(allow_null=True)
    active_scanner_assignments = MemberAreaScannerAssignmentSerializer(many=True)


class ExistingAccountAdmissionSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="user",
    )
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
            return admit_existing_account(
                admitted_by=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class MemberTransferSerializer(serializers.Serializer):
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        source="new_department",
    )
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.filter(is_active=True),
        source="new_position",
    )
    reason = serializers.CharField(max_length=1000)

    def create(self, validated_data):
        try:
            return transfer_member(
                membership=self.context["membership"],
                assigned_by=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class OnboardingStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(
            OnboardingStatus.IN_PROGRESS,
            OnboardingStatus.COMPLETED,
        )
    )

    def create(self, validated_data):
        try:
            return update_onboarding_status(
                membership=self.context["membership"],
                new_status=validated_data["status"],
                updated_by=self.context["request"].user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class MemberDepartureSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)

    def create(self, validated_data):
        try:
            return record_member_departure(
                membership=self.context["membership"],
                recorded_by=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
