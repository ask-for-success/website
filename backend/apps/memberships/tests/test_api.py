from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.events.models import Event, EventScanner, PublicationStatus
from apps.organization.models import Department, Position

from ..models import Membership, MembershipStatus, OnboardingStatus


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

    def test_onboarding_must_start_before_completion_and_then_activates_member(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]

        premature_response = self.client.patch(
            f"/api/v1/memberships/{membership_id}/onboarding/",
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )
        start_response = self.client.patch(
            f"/api/v1/memberships/{membership_id}/onboarding/",
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )
        completion_response = self.client.patch(
            f"/api/v1/memberships/{membership_id}/onboarding/",
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )

        self.assertEqual(
            premature_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(start_response.data["onboarding"]["started_at"])
        self.assertEqual(completion_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            completion_response.data["status"],
            MembershipStatus.ACTIVE,
        )
        self.assertEqual(
            completion_response.data["onboarding"]["status"],
            OnboardingStatus.COMPLETED,
        )
        self.assertIsNotNone(
            completion_response.data["onboarding"]["completed_at"]
        )

    def test_completed_onboarding_cannot_be_reopened(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        onboarding_url = f"/api/v1/memberships/{membership_id}/onboarding/"
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )

        response = self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_departure_inactivates_membership_and_preserves_history(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        onboarding_url = f"/api/v1/memberships/{membership_id}/onboarding/"
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )

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

    def test_member_area_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_without_membership_receives_empty_member_area(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.get("/api/v1/memberships/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["membership"])
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

    def test_member_area_lists_only_active_upcoming_scanner_assignments(self):
        creation = self.admit_candidate()
        membership_id = creation.data["id"]
        onboarding_url = f"/api/v1/memberships/{membership_id}/onboarding/"
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.IN_PROGRESS},
            format="json",
        )
        self.client.patch(
            onboarding_url,
            {"status": OnboardingStatus.COMPLETED},
            format="json",
        )
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
