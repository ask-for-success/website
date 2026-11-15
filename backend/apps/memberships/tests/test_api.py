from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditRecord
from apps.events.models import Event, EventScanner, PublicationStatus
from apps.organization.models import Department, Position

from ..models import (
    MemberIdentity,
    Membership,
    MembershipStatus,
    OnboardingStatus,
)


class MembershipLifecycleApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr_manager = User.objects.create_user(
            email="membership-hr@example.com",
            first_name="Membership",
            last_name="Manager",
            phone_number="+212600000801",
            password="StrongPassword!2026",
        )
        cls.hr_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.hr_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.account_administrator = User.objects.create_user(
            email="membership-admin@example.com",
            first_name="Membership",
            last_name="Administrator",
            phone_number="+212600000805",
            password="StrongPassword!2026",
        )
        cls.account_administrator.groups.add(
            Group.objects.get(name="account_administrator")
        )
        cls.ordinary_user = User.objects.create_user(
            email="membership-ordinary@example.com",
            first_name="Ordinary",
            last_name="User",
            phone_number="+212600000802",
            password="StrongPassword!2026",
        )
        cls.candidate = User.objects.create_user(
            email="accepted-candidate@example.com",
            first_name="Accepted",
            last_name="Candidate",
            phone_number="+212600000803",
            password="StrongPassword!2026",
        )
        cls.other_candidate = User.objects.create_user(
            email="second-candidate@example.com",
            first_name="Second",
            last_name="Candidate",
            phone_number="+212600000804",
            password="StrongPassword!2026",
        )
        cls.technology = Department.objects.create(name="Technology")
        cls.developer = Position.objects.create(
            department=cls.technology,
            name="Developer",
        )
        cls.marketing = Department.objects.create(name="Marketing")
        cls.marketing_manager = Position.objects.create(
            department=cls.marketing,
            name="Marketing manager",
        )

    def admission_payload(self, user=None):
        return {
            "user_id": str((user or self.candidate).id),
            "department_id": str(self.technology.id),
            "position_id": str(self.developer.id),
        }

    def admit_candidate(self, user=None):
        self.client.force_authenticate(self.hr_manager)
        return self.client.post(
            "/api/v1/memberships/admissions/",
            self.admission_payload(user),
            format="json",
        )

    def complete_self_onboarding(
        self,
        user=None,
        national_id_number="AB123456",
    ):
        self.client.force_authenticate(user or self.candidate)
        return self.client.post(
            "/api/v1/memberships/me/onboarding/",
            {"national_id_number": national_id_number},
            format="json",
        )

    def test_hr_manager_admits_existing_account(self):
        response = self.admit_candidate()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        membership = Membership.objects.get(user=self.candidate)
        self.assertEqual(membership.status, MembershipStatus.PENDING_ONBOARDING)
        self.assertEqual(membership.onboarding.status, OnboardingStatus.NOT_STARTED)
        assignment = membership.assignments.get(ends_at__isnull=True)
        self.assertEqual(assignment.department, self.technology)
        self.assertEqual(assignment.position, self.developer)
        self.assertEqual(assignment.assigned_by, self.hr_manager)
        self.assertEqual(
            response.data["current_assignment"]["department"]["name"],
            "Technology",
        )

    def test_same_account_cannot_be_admitted_twice(self):
        first_response = self.admit_candidate()
        second_response = self.admit_candidate()

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Membership.objects.filter(user=self.candidate).count(), 1)

    def test_ordinary_user_cannot_manage_memberships(self):
        self.client.force_authenticate(self.ordinary_user)

        list_response = self.client.get("/api/v1/memberships/")
        admission_response = self.client.post(
            "/api/v1/memberships/admissions/",
            self.admission_payload(),
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(admission_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_and_detail_include_current_assignment_and_history(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]

        list_response = self.client.get(
            "/api/v1/memberships/",
            {"search": "accepted-candidate", "department_id": self.technology.id},
        )
        detail_response = self.client.get(
            f"/api/v1/memberships/{membership_id}/"
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["assignment_history"], [])
        self.assertEqual(
            detail_response.data["user"]["email"],
            self.candidate.email,
        )

    def test_transfer_closes_previous_assignment_and_preserves_onboarding(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        membership = Membership.objects.get(pk=membership_id)
        onboarding_id = membership.onboarding.id

        response = self.client.post(
            f"/api/v1/memberships/{membership_id}/transfers/",
            {
                "department_id": str(self.marketing.id),
                "position_id": str(self.marketing_manager.id),
                "reason": "Accepted into the marketing department",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        self.assertEqual(membership.onboarding.id, onboarding_id)
        self.assertEqual(
            membership.assignments.filter(ends_at__isnull=True).count(),
            1,
        )
        self.assertEqual(
            response.data["current_assignment"]["department"]["name"],
            "Marketing",
        )
        self.assertEqual(len(response.data["assignment_history"]), 1)
        self.assertEqual(
            response.data["assignment_history"][0]["end_reason"],
            "Accepted into the marketing department",
        )

    def test_member_completes_mandatory_onboarding_and_activates_membership(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]

        hr_completion_response = self.client.patch(
            f"/api/v1/memberships/{membership_id}/onboarding/",
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )
        self.client.force_authenticate(self.candidate)
        before_response = self.client.get("/api/v1/memberships/me/")
        completion_response = self.complete_self_onboarding(
            national_id_number="ab123456"
        )

        self.assertEqual(
            hr_completion_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(before_response.data["onboarding_required"])
        self.assertFalse(before_response.data["can_access_member_features"])
        self.assertEqual(completion_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            completion_response.data["membership"]["status"],
            MembershipStatus.ACTIVE,
        )
        self.assertEqual(
            completion_response.data["membership"]["onboarding"]["status"],
            OnboardingStatus.COMPLETED,
        )
        self.assertFalse(completion_response.data["onboarding_required"])
        self.assertTrue(completion_response.data["can_access_member_features"])
        self.assertTrue(
            completion_response.data["membership"]["national_id_collected"]
        )
        self.assertIsNotNone(
            completion_response.data["membership"]["onboarding"]["started_at"]
        )
        self.assertIsNotNone(
            completion_response.data["membership"]["onboarding"]["completed_at"]
        )
        self.assertNotIn("AB123456", str(completion_response.data))
        identity = MemberIdentity.objects.get(membership_id=membership_id)
        self.assertEqual(identity.national_id_number, "AB123456")

    def test_completed_onboarding_cannot_be_reopened(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        onboarding_url = f"/api/v1/memberships/{membership_id}/onboarding/"
        self.complete_self_onboarding()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_departure_inactivates_membership_and_preserves_history(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        self.complete_self_onboarding()
        self.client.force_authenticate(self.hr_manager)

        response = self.client.post(
            f"/api/v1/memberships/{membership_id}/departures/",
            {"reason": "Member left the association"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], MembershipStatus.INACTIVE)
        self.assertIsNone(response.data["current_assignment"])
        self.assertEqual(len(response.data["assignment_history"]), 1)
        self.assertEqual(
            response.data["assignment_history"][0]["end_reason"],
            "Member left the association",
        )
        self.candidate.refresh_from_db()
        self.assertTrue(self.candidate.is_active)

    def test_departure_requires_active_membership(self):
        creation = self.admit_candidate()

        response = self.client.post(
            f"/api/v1/memberships/{creation.data['id']}/departures/",
            {"reason": "Not active yet"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_rejects_position_from_another_department(self):
        creation = self.admit_candidate()

        response = self.client.post(
            f"/api/v1/memberships/{creation.data['id']}/transfers/",
            {
                "department_id": str(self.marketing.id),
                "position_id": str(self.developer.id),
                "reason": "Invalid department and position pair",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("position", response.data)

    def test_schema_documents_membership_lifecycle_routes(self):
        response = self.client.get(
            "/api/schema/",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/memberships/", response.data["paths"])
        self.assertIn(
            "/api/v1/memberships/admissions/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/memberships/{membership_id}/transfers/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/memberships/{membership_id}/onboarding/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/memberships/{membership_id}/departures/",
            response.data["paths"],
        )
        self.assertIn("/api/v1/memberships/me/", response.data["paths"])
        self.assertIn(
            "/api/v1/memberships/me/onboarding/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/memberships/{membership_id}/identity/",
            response.data["paths"],
        )

    def test_member_area_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_without_membership_receives_empty_member_area(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["membership"])
        self.assertFalse(response.data["onboarding_required"])
        self.assertFalse(response.data["can_access_member_features"])
        self.assertEqual(response.data["active_scanner_assignments"], [])

    def test_member_area_returns_only_the_current_accounts_safe_membership(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        self.client.post(
            f"/api/v1/memberships/{membership_id}/transfers/",
            {
                "department_id": str(self.marketing.id),
                "position_id": str(self.marketing_manager.id),
                "reason": "Internal HR transfer reason",
            },
            format="json",
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = response.data["membership"]
        self.assertEqual(membership["id"], membership_id)
        self.assertEqual(
            membership["current_assignment"]["department"]["name"],
            "Marketing",
        )
        self.assertEqual(len(membership["assignment_history"]), 1)
        self.assertNotIn("assigned_by", membership["current_assignment"])
        self.assertNotIn("end_reason", membership["assignment_history"][0])
        self.assertNotIn("user", membership)
        self.assertFalse(membership["national_id_collected"])
        self.assertTrue(response.data["onboarding_required"])
        self.assertFalse(response.data["can_access_member_features"])

    def test_self_onboarding_requires_an_accepted_membership(self):
        response = self.complete_self_onboarding(user=self.ordinary_user)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("membership", response.data)

    def test_self_onboarding_rejects_invalid_or_duplicate_national_id(self):
        self.admit_candidate()
        invalid_response = self.complete_self_onboarding(
            national_id_number="invalid-id"
        )
        valid_response = self.complete_self_onboarding()
        self.admit_candidate(user=self.other_candidate)
        duplicate_response = self.complete_self_onboarding(
            user=self.other_candidate,
            national_id_number="ab123456",
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            duplicate_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        other_membership = Membership.objects.get(user=self.other_candidate)
        self.assertEqual(
            other_membership.status,
            MembershipStatus.PENDING_ONBOARDING,
        )
        self.assertFalse(
            MemberIdentity.objects.filter(membership=other_membership).exists()
        )

    def test_protected_identity_read_requires_hr_or_account_administrator(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        self.complete_self_onboarding()
        identity_url = f"/api/v1/memberships/{membership_id}/identity/"

        candidate_response = self.client.get(identity_url)
        self.client.force_authenticate(self.ordinary_user)
        ordinary_response = self.client.get(identity_url)
        self.client.force_authenticate(self.hr_manager)
        hr_response = self.client.get(identity_url)
        self.client.force_authenticate(self.account_administrator)
        administrator_response = self.client.get(identity_url)

        self.assertEqual(candidate_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(ordinary_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(hr_response.status_code, status.HTTP_200_OK)
        self.assertEqual(administrator_response.status_code, status.HTTP_200_OK)
        self.assertEqual(hr_response.data["national_id_number"], "AB123456")
        read_records = AuditRecord.objects.filter(
            membership_id=membership_id,
            action=AuditAction.NATIONAL_ID_VIEWED,
        )
        self.assertEqual(read_records.count(), 2)
        self.assertTrue(
            all(
                "AB123456" not in str(record.new_state)
                for record in read_records
            )
        )

    def test_member_area_lists_only_active_upcoming_scanner_assignments(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        self.complete_self_onboarding()
        membership = Membership.objects.get(pk=membership_id)
        now = timezone.now()
        upcoming_event = Event.objects.create(
            title="Upcoming scanner event",
            summary="An upcoming event.",
            description="Scanner access should appear.",
            location="Casablanca",
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=2, hours=3),
            publication_status=PublicationStatus.PUBLISHED,
            requires_qr_code=True,
            created_by=self.hr_manager,
        )
        past_event = Event.objects.create(
            title="Past scanner event",
            summary="A past event.",
            description="Scanner access should not appear.",
            location="Rabat",
            starts_at=now - timedelta(days=2),
            ends_at=now - timedelta(days=2, hours=-3),
            publication_status=PublicationStatus.PUBLISHED,
            requires_qr_code=True,
            created_by=self.hr_manager,
        )
        inactive_event = Event.objects.create(
            title="Inactive scanner assignment",
            summary="An inactive scanner assignment.",
            description="Scanner access should not appear.",
            location="Marrakesh",
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=3),
            publication_status=PublicationStatus.PUBLISHED,
            requires_qr_code=True,
            created_by=self.hr_manager,
        )
        EventScanner.objects.create(
            event=upcoming_event,
            membership=membership,
            assigned_by=self.hr_manager,
        )
        EventScanner.objects.create(
            event=past_event,
            membership=membership,
            assigned_by=self.hr_manager,
        )
        EventScanner.objects.create(
            event=inactive_event,
            membership=membership,
            assigned_by=self.hr_manager,
            is_active=False,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignments = response.data["active_scanner_assignments"]
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["event"]["id"], str(upcoming_event.id))
        self.assertEqual(
            assignments[0]["event"]["title"],
            "Upcoming scanner event",
        )
