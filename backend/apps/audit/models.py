import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditDomain(models.TextChoices):
    ACCOUNTS = "accounts", "Accounts"
    ACCESS_CONTROL = "access_control", "Access control"
    ORGANIZATION = "organization", "Organization"
    CONTENT = "content", "Content"
    EVENTS = "events", "Events"
    RECRUITMENT = "recruitment", "Recruitment"
    MEMBERSHIP = "membership", "Membership"


class AuditAction(models.TextChoices):
    ACCOUNT_REGISTERED = "accounts.registered", "Account registered"
    ACCOUNT_LOGIN = "accounts.login", "Account login"
    ACCOUNT_INVITATION_CREATED = (
        "accounts.invitation_created",
        "Account invitation created",
    )
    ACCOUNT_INVITATION_ACCEPTED = (
        "accounts.invitation_accepted",
        "Account invitation accepted",
    )
    ACCOUNT_DEACTIVATED = (
        "accounts.deactivated",
        "Account deactivated",
    )
    ACCESS_ASSIGNMENT_CHANGED = (
        "access_control.assignment_changed",
        "Access assignment changed",
    )
    API_CREATED = "api.created", "API record created"
    API_UPDATED = "api.updated", "API record updated"
    API_DELETED = "api.deleted", "API record deleted"
    API_ACTION_PERFORMED = "api.action_performed", "API action performed"
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
    NATIONAL_ID_SUBMITTED = (
        "membership.national_id_submitted",
        "National ID submitted",
    )
    NATIONAL_ID_VIEWED = (
        "membership.national_id_viewed",
        "National ID viewed",
    )


ALLOWED_STATE_KEYS = {
    "account_active",
    "account_administrator_access",
    "content_manager_access",
    "hr_access",
    "staff_access",
    "application_status",
    "membership_status",
    "onboarding_status",
    "invitation_status",
    "national_id_collected",
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
    target_type = models.CharField(max_length=150, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    operation = models.CharField(max_length=180, blank=True)
    request_method = models.CharField(max_length=8, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
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
                    | ~models.Q(target_type="")
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
        self.target_type = self.target_type.strip()
        self.operation = self.operation.strip()
        self.request_method = self.request_method.strip().upper()
        self.request_path = self.request_path.strip()
        if (
            self.action == AuditAction.APPLICATION_STATUS_CHANGED
            and not self.application_id
        ):
            raise ValidationError(
                {"application": "A recruitment audit requires an application."}
            )
        membership_actions = {
            AuditAction.MEMBERSHIP_CREATED,
            AuditAction.MEMBERSHIP_REACTIVATED,
            AuditAction.MEMBERSHIP_TRANSFERRED,
            AuditAction.ONBOARDING_STATUS_CHANGED,
            AuditAction.DEPARTURE_RECORDED,
            AuditAction.INVITATION_CREATED,
            AuditAction.INVITATION_ACCEPTED,
            AuditAction.NATIONAL_ID_SUBMITTED,
            AuditAction.NATIONAL_ID_VIEWED,
        }
        if self.action in membership_actions and not self.membership_id:
            raise ValidationError(
                {"membership": "A membership audit requires a membership."}
            )
        if (
            not self.application_id
            and not self.membership_id
            and not self.target_type
        ):
            raise ValidationError(
                {"target_type": "An audit record requires a business target."}
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
