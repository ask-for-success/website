import uuid

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.organization.models import Department, Position


class OrganizationModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="Technology",
            description="Technology department",
        )

    def test_department_uses_uuid_primary_key(self):
        self.assertIsInstance(self.department.id, uuid.UUID)

    def test_department_name_is_unique_case_insensitively(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Department.objects.create(name="TECHNOLOGY")

    def test_position_belongs_to_one_department(self):
        position = Position.objects.create(
            department=self.department,
            name="Developer",
        )

        self.assertEqual(position.department, self.department)
        self.assertQuerySetEqual(self.department.positions.all(), [position])

    def test_position_name_is_unique_within_department(self):
        Position.objects.create(
            department=self.department,
            name="Developer",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Position.objects.create(
                department=self.department,
                name="DEVELOPER",
            )

    def test_same_position_name_is_allowed_in_two_departments(self):
        other_department = Department.objects.create(name="Marketing")
        first_position = Position.objects.create(
            department=self.department,
            name="Manager",
        )
        second_position = Position.objects.create(
            department=other_department,
            name="Manager",
        )

        self.assertNotEqual(
            first_position.department,
            second_position.department,
        )

    def test_department_deletion_is_protected_when_referenced(self):
        Position.objects.create(
            department=self.department,
            name="Developer",
        )

        with self.assertRaises(ProtectedError):
            self.department.delete()

    def test_department_and_position_can_be_deactivated(self):
        position = Position.objects.create(
            department=self.department,
            name="Developer",
        )
        self.department.is_active = False
        self.department.save(update_fields=("is_active", "updated_at"))
        position.is_active = False
        position.save(update_fields=("is_active", "updated_at"))

        self.department.refresh_from_db()
        position.refresh_from_db()
        self.assertFalse(self.department.is_active)
        self.assertFalse(position.is_active)
