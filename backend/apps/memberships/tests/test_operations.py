from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.organization.models import Department, Position

from ..models import OnboardingStatus
from ..operations import create_initial_membership, transfer_member


class MembershipOperationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(
            email="candidate@example.com",
            first_name="Accepted",
            last_name="Candidate",
            phone_number="+212600000301",
            password="StrongPassword!2026",
        )
        cls.hr_manager = User.objects.create_user(
            email="hr@example.com",
            first_name="Authorized",
            last_name="Manager",
            phone_number="+212600000302",
            password="StrongPassword!2026",
        )
        cls.hr_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.hr_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.ordinary_user = User.objects.create_user(
            email="ordinary@example.com",
            first_name="Ordinary",
            last_name="User",
            phone_number="+212600000303",
            password="StrongPassword!2026",
        )
        cls.initial_department = Department.objects.create(name="Technology")
        cls.initial_position = Position.objects.create(
            department=cls.initial_department,
            name="Developer",
        )
        cls.new_department = Department.objects.create(name="Marketing")
        cls.new_position = Position.objects.create(
            department=cls.new_department,
            name="Marketing manager",
        )

    def create_membership(self):
        return create_initial_membership(
            user=self.member,
            department=self.initial_department,
            position=self.initial_position,
            assigned_by=self.hr_manager,
        )

    def test_initial_creation_adds_onboarding_and_assignment(self):
        membership = self.create_membership()

        self.assertEqual(membership.onboarding.status, OnboardingStatus.NOT_STARTED)
        assignment = membership.assignments.get()
        self.assertEqual(assignment.department, self.initial_department)
        self.assertEqual(assignment.position, self.initial_position)
        self.assertEqual(assignment.assigned_by, self.hr_manager)

    def test_initial_creation_requires_hr_permission(self):
        with self.assertRaises(PermissionDenied):
            create_initial_membership(
                user=self.member,
                department=self.initial_department,
                position=self.initial_position,
                assigned_by=self.ordinary_user,
            )

    def test_transfer_closes_old_assignment_and_creates_new_one(self):
        membership = self.create_membership()
        onboarding_id = membership.onboarding.id

        new_assignment = transfer_member(
            membership=membership,
            new_department=self.new_department,
            new_position=self.new_position,
            assigned_by=self.hr_manager,
            reason="Accepted into the marketing department",
        )

        old_assignment = membership.assignments.exclude(id=new_assignment.id).get()
        self.assertIsNotNone(old_assignment.ends_at)
        self.assertEqual(
            old_assignment.end_reason,
            "Accepted into the marketing department",
        )
        self.assertEqual(new_assignment.department, self.new_department)
        self.assertEqual(new_assignment.position, self.new_position)
        membership.onboarding.refresh_from_db()
        self.assertEqual(membership.onboarding.id, onboarding_id)
        self.assertEqual(
            membership.assignments.filter(ends_at__isnull=True).count(),
            1,
        )

    def test_transfer_requires_reason(self):
        membership = self.create_membership()

        with self.assertRaises(ValidationError):
            transfer_member(
                membership=membership,
                new_department=self.new_department,
                new_position=self.new_position,
                assigned_by=self.hr_manager,
                reason="   ",
            )

    def test_transfer_requires_hr_permission(self):
        membership = self.create_membership()

        with self.assertRaises(PermissionDenied):
            transfer_member(
                membership=membership,
                new_department=self.new_department,
                new_position=self.new_position,
                assigned_by=self.ordinary_user,
                reason="Unauthorized transfer",
            )

    def test_transfer_rejects_position_from_another_department(self):
        membership = self.create_membership()

        with self.assertRaises(ValidationError):
            transfer_member(
                membership=membership,
                new_department=self.new_department,
                new_position=self.initial_position,
                assigned_by=self.hr_manager,
                reason="Inconsistent position",
            )
