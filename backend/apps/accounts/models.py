import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=32, unique=True)
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
            )
        ]

    def clean(self) -> None:
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        self.phone_number = self.phone_number.strip()

    def __str__(self) -> str:
        return self.email
