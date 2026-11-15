import uuid

from django.db import models
from django.db.models.functions import Lower


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "departments"
        ordering = ("name",)
        constraints = (
            models.UniqueConstraint(
                Lower("name"),
                name="departments_name_unique_case_insensitive",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()

    def __str__(self) -> str:
        return self.name


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="positions",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "positions"
        ordering = ("department__name", "name")
        constraints = (
            models.UniqueConstraint(
                models.F("department"),
                Lower("name"),
                name="positions_department_name_unique_case_insensitive",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()

    def __str__(self) -> str:
        return f"{self.department.name} — {self.name}"
