import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class AccountInvitationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    USED = "used", "Used"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class AccountInvitationPurpose(models.TextChoices):
    INITIAL_SETUP = "initial_setup", "Initial setup"
    REACTIVATION = "reactivation", "Reactivation"


class AccountInvitationEmailStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number"]

    class Meta:
        db_table = "users"
        ordering = ("email",)
        permissions = (
            ("manage_accounts", "Can manage user accounts"),
            ("manage_access_assignments", "Can manage access assignments"),
            ("manage_content", "Can manage CMS content"),
            ("manage_hr", "Can manage HR operations"),
            ("view_audit_log", "Can view the audit log"),
        )
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="users_email_case_insensitive_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_active=False)
                    | (
                        models.Q(phone_number__isnull=False)
                        & ~models.Q(phone_number="")
                    )
                ),
                name="active_users_require_phone_number",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        if self.phone_number:
            self.phone_number = self.phone_number.strip()
        elif self.is_active:
            raise ValidationError(
                {"phone_number": "An active account must have a phone number."}
            )

    def __str__(self) -> str:
        return self.email


class AccountInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="account_invitations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_account_invitations",
    )
    purpose = models.CharField(
        max_length=24,
        choices=AccountInvitationPurpose.choices,
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(
        max_length=16,
        choices=AccountInvitationStatus.choices,
        default=AccountInvitationStatus.ACTIVE,
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    email_delivery_status = models.CharField(
        max_length=16,
        choices=AccountInvitationEmailStatus.choices,
        default=AccountInvitationEmailStatus.PENDING,
    )
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "account_invitations"
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status=AccountInvitationStatus.ACTIVE),
                name="account_invitations_one_active_per_user",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.status == AccountInvitationStatus.ACTIVE
            and self.user_id
            and self.user.is_active
        ):
            raise ValidationError(
                {"user": "An active account cannot have a setup invitation."}
            )

    def __str__(self) -> str:
        return f"Account invitation for {self.user.email}"
