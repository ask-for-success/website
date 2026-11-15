import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditDomain(models.TextChoices):
    RECRUITMENT = "recruitment", "Recruitment"
    MEMBERSHIP = "membership", "Membership"


class AuditAction(models.TextChoices):
    APPLICATION_STATUS_CHANGED = (
        "recruitment.application_status_changed",
        "Application status changed",
    )
    MEMBERSHIP_CREATED = "membership.created", "Membership created"
    MEMBERSHIP_REACTIVATED = (
        "membership.reactivated",
        "Membership reactivated",
    )
    MEMBERSHIP_TRANSFERRED = (
        "membership.transferred",
        "Membership transferred",
    )
    ONBOARDING_STATUS_CHANGED = (
        "membership.onboarding_status_changed",
        "Onboarding status changed",
    )
    DEPARTURE_RECORDED = (
        "membership.departure_recorded",
        "Membership departure recorded",
    )
    INVITATION_CREATED = (
        "membership.invitation_created",
        "Membership invitation created",
    )
    INVITATION_ACCEPTED = (
        "membership.invitation_accepted",
        "Membership invitation accepted",
    )


ALLOWED_STATE_KEYS = {
    "application_status",
    "membership_status",
    "onboarding_status",
    "invitation_status",
    "department_id",
    "position_id",
    "assignment_id",
}


class AuditRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.CharField(max_length=24, choices=AuditDomain.choices)
    action = models.CharField(max_length=64, choices=AuditAction.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_records",
    )
    application = models.ForeignKey(
        "recruitment.RecruitmentApplication",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_records",
    )
    membership = models.ForeignKey(
        "memberships.Membership",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_records",
    )
    previous_state = models.JSONField(default=dict, blank=True)
    new_state = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_records"
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(fields=("domain", "action", "created_at")),
            models.Index(fields=("actor", "created_at")),
            models.Index(fields=("application", "created_at")),
            models.Index(fields=("membership", "created_at")),
        )
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(application__isnull=False)
                    | models.Q(membership__isnull=False)
                ),
                name="audit_records_require_target",
            ),
        )

    @staticmethod
    def _validate_state(field_name: str, state) -> None:
        if not isinstance(state, dict):
            raise ValidationError({field_name: "Audit state must be an object."})
        unsafe_keys = set(state) - ALLOWED_STATE_KEYS
        if unsafe_keys:
            raise ValidationError(
                {
                    field_name: (
                        "Unsupported audit state keys: "
                        + ", ".join(sorted(unsafe_keys))
                    )
                }
            )
        if any(isinstance(value, (dict, list)) for value in state.values()):
            raise ValidationError(
                {field_name: "Audit state values must be scalar values."}
            )

    def clean(self) -> None:
        super().clean()
        self.reason = self.reason.strip()
        if self.domain == AuditDomain.RECRUITMENT and not self.application_id:
            raise ValidationError(
                {"application": "A recruitment audit requires an application."}
            )
        if self.domain == AuditDomain.MEMBERSHIP and not self.membership_id:
            raise ValidationError(
                {"membership": "A membership audit requires a membership."}
            )
        self._validate_state("previous_state", self.previous_state)
        self._validate_state("new_state", self.new_state)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit records are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit records cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.action} by {self.actor.email}"
