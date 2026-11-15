from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.organization.models import Department, Position

from ..models import (
    MemberAssignment,
    Membership,
    MembershipOnboarding,
    MembershipStatus,
    OnboardingStatus,
)


class MembershipModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(
            email="member@example.com",
            first_name="Active",
            last_name="Member",
            phone_number="+212600000201",
            password="StrongPassword!2026",
        )
        cls.manager = User.objects.create_user(
            email="manager@example.com",
            first_name="Assignment",
            last_name="Manager",
            phone_number="+212600000202",
            password="StrongPassword!2026",
        )
        cls.department = Department.objects.create(name="Technology")
        cls.position = Position.objects.create(
            department=cls.department,
            name="Developer",
        )

    def test_user_has_only_one_membership(self):
        Membership.objects.create(user=self.member)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Membership.objects.create(user=self.member)

    def test_membership_starts_pending_onboarding(self):
        membership = Membership.objects.create(user=self.member)

        self.assertEqual(membership.status, MembershipStatus.PENDING_ONBOARDING)

    def test_membership_has_only_one_onboarding_record(self):
        membership = Membership.objects.create(user=self.member)
        onboarding = MembershipOnboarding.objects.create(membership=membership)

        with self.assertRaises(IntegrityError), transaction.atomic():
            MembershipOnboarding.objects.create(membership=membership)

    def test_onboarding_starts_not_started(self):
        membership = Membership.objects.create(user=self.member)
        onboarding = MembershipOnboarding.objects.create(membership=membership)

        self.assertEqual(onboarding.status, OnboardingStatus.NOT_STARTED)

    def test_membership_has_only_one_active_assignment(self):
        membership = Membership.objects.create(user=self.member)
        MemberAssignment.objects.create(
            membership=membership,
            department=self.department,
            position=self.position,
            assigned_by=self.manager,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            MemberAssignment.objects.create(
                membership=membership,
                department=self.department,
                position=self.position,
                assigned_by=self.manager,
            )

    def test_position_must_belong_to_assignment_department(self):
        membership = Membership.objects.create(user=self.member)
        other_department = Department.objects.create(name="Marketing")
        assignment = MemberAssignment(
            membership=membership,
            department=other_department,
            position=self.position,
            assigned_by=self.manager,
        )

        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_new_assignment_is_allowed_after_previous_one_ends(self):
        membership = Membership.objects.create(user=self.member)
        old_assignment = MemberAssignment.objects.create(
            membership=membership,
            department=self.department,
            position=self.position,
            assigned_by=self.manager,
        )
        old_assignment.ends_at = timezone.now()
        old_assignment.end_reason = "Department transfer"
        old_assignment.save(
            update_fields=("ends_at", "end_reason", "updated_at")
        )
        new_department = Department.objects.create(name="Marketing")
        new_position = Position.objects.create(
            department=new_department,
            name="Marketing manager",
        )

        new_assignment = MemberAssignment.objects.create(
            membership=membership,
            department=new_department,
            position=new_position,
            assigned_by=self.manager,
        )

        self.assertIsNone(new_assignment.ends_at)
        self.assertEqual(membership.assignments.count(), 2)

    def test_assignment_end_must_follow_start(self):
        membership = Membership.objects.create(user=self.member)
        now = timezone.now()
        assignment = MemberAssignment(
            membership=membership,
            department=self.department,
            position=self.position,
            assigned_by=self.manager,
            starts_at=now,
            ends_at=now - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            assignment.full_clean()
