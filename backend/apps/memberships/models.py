import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.organization.models import Department, Position


class MembershipStatus(models.TextChoices):
    PENDING_ONBOARDING = "pending_onboarding", "Pending onboarding"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class OnboardingStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class MembershipInvitationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    USED = "used", "Used"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="membership",
    )
    status = models.CharField(
        max_length=32,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING_ONBOARDING,
    )
    accepted_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "memberships"
        ordering = ("-accepted_at",)

    def __str__(self) -> str:
        return f"Membership for {self.user.email}"


class MembershipOnboarding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.OneToOneField(
        Membership,
        on_delete=models.CASCADE,
        related_name="onboarding",
    )
    status = models.CharField(
        max_length=16,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.NOT_STARTED,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "membership_onboarding"

    def __str__(self) -> str:
        return f"Onboarding for {self.membership.user.email}"


class MemberIdentity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.OneToOneField(
        Membership,
        on_delete=models.PROTECT,
        related_name="identity",
    )
    national_id_number = models.CharField(
        max_length=20,
        unique=True,
        validators=(
            RegexValidator(
                regex=r"^[A-Za-z0-9]{4,20}$",
                message=(
                    "National ID number must contain 4 to 20 letters and digits."
                ),
            ),
        ),
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "member_identities"

    def clean(self) -> None:
        super().clean()
        self.national_id_number = self.national_id_number.strip().upper()

    def save(self, *args, **kwargs):
        self.national_id_number = self.national_id_number.strip().upper()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Protected identity for {self.membership.user.email}"


class MembershipInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="invitations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="membership_invitations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_membership_invitations",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=16,
        choices=MembershipInvitationStatus.choices,
        default=MembershipInvitationStatus.ACTIVE,
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "membership_invitations"
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status=MembershipInvitationStatus.ACTIVE),
                name="membership_invitations_one_active_per_user",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.membership_id
            and self.user_id
            and self.membership.user_id != self.user_id
        ):
            raise ValidationError(
                {"user": "The invitation user must own the membership."}
            )

    def __str__(self) -> str:
        return f"Membership invitation for {self.user.email}"


class MemberAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="member_assignments",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="member_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_member_positions",
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "member_assignments"
        ordering = ("-starts_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("membership",),
                condition=models.Q(ends_at__isnull=True),
                name="member_assignments_one_active_per_membership",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.position_id
            and self.department_id
            and self.position.department_id != self.department_id
        ):
            raise ValidationError(
                {"position": "The position must belong to the selected department."}
            )
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "The end time must be after the start time."}
            )

    def __str__(self) -> str:
        return (
            f"{self.membership.user.email} — "
            f"{self.department.name} — {self.position.name}"
        )
