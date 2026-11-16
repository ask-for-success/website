from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.organization.models import Department, Position

from ..models import (
    InvitationEmailStatus,
    MembershipInvitation,
    MembershipInvitationStatus,
    OnboardingStatus,
)
from ..operations import (
    accept_membership_invitation,
    create_membership_invitation,
)


class MembershipInvitationDataMixin:
    @classmethod
    def create_common_data(cls):
        cls.hr_manager = User.objects.create_user(
            email="hr-manager@example.com",
            first_name="HR",
            last_name="Manager",
            phone_number="+212600000401",
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
            email="unauthorized@example.com",
            first_name="Unauthorized",
            last_name="User",
            phone_number="+212600000402",
            password="StrongPassword!2026",
        )
        cls.department = Department.objects.create(name="Communications")
        cls.position = Position.objects.create(
            department=cls.department,
            name="Media manager",
        )

    def invitation_data(self, **overrides):
        data = {
            "email": "invited-member@example.com",
            "first_name": "Invited",
            "last_name": "Member",
            "department": self.department,
            "position": self.position,
            "created_by": self.hr_manager,
        }
        data.update(overrides)
        return data


class MembershipInvitationOperationTests(
    MembershipInvitationDataMixin,
    TestCase,
):
    @classmethod
    def setUpTestData(cls):
        cls.create_common_data()

    def test_creation_prepares_account_membership_assignment_and_onboarding(self):
        result = create_membership_invitation(**self.invitation_data())

        user = result.invitation.user
        self.assertFalse(user.is_active)
        self.assertIsNone(user.phone_number)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(result.invitation.membership.user, user)
        self.assertEqual(
            result.invitation.membership.onboarding.status,
            OnboardingStatus.NOT_STARTED,
        )
        assignment = result.invitation.membership.assignments.get()
        self.assertEqual(assignment.department, self.department)
        self.assertEqual(assignment.position, self.position)
        self.assertEqual(
            result.invitation.email_delivery_status,
            InvitationEmailStatus.PENDING,
        )

    def test_raw_token_is_never_stored(self):
        result = create_membership_invitation(**self.invitation_data())

        self.assertNotEqual(result.invitation.token_hash, result.setup_token)
        self.assertEqual(len(result.invitation.token_hash), 64)
        lifetime = result.invitation.expires_at - timezone.now()
        self.assertGreater(lifetime, timedelta(hours=47, minutes=59))
        self.assertLessEqual(lifetime, timedelta(hours=48))

    def test_acceptance_activates_account_and_consumes_token(self):
        result = create_membership_invitation(**self.invitation_data())

        user = accept_membership_invitation(
            token=result.setup_token,
            phone_number="+212600000403",
            password="NewStrongPassword!2026",
        )

        user.refresh_from_db()
        result.invitation.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.phone_number, "+212600000403")
        self.assertTrue(user.check_password("NewStrongPassword!2026"))
        self.assertEqual(
            result.invitation.status,
            MembershipInvitationStatus.USED,
        )
        self.assertIsNotNone(result.invitation.used_at)
        with self.assertRaises(ValidationError):
            accept_membership_invitation(
                token=result.setup_token,
                phone_number="+212600000404",
                password="AnotherStrongPassword!2026",
            )

    def test_reissuing_invitation_cancels_previous_one(self):
        first_result = create_membership_invitation(**self.invitation_data())
        second_result = create_membership_invitation(**self.invitation_data())

        first_result.invitation.refresh_from_db()
        self.assertEqual(
            first_result.invitation.status,
            MembershipInvitationStatus.CANCELLED,
        )
        self.assertIsNotNone(first_result.invitation.cancelled_at)
        self.assertEqual(
            first_result.invitation.membership_id,
            second_result.invitation.membership_id,
        )
        self.assertNotEqual(first_result.setup_token, second_result.setup_token)
        self.assertEqual(
            MembershipInvitation.objects.filter(
                user=second_result.invitation.user,
                status=MembershipInvitationStatus.ACTIVE,
            ).count(),
            1,
        )

    def test_expired_invitation_is_marked_and_rejected(self):
        result = create_membership_invitation(**self.invitation_data())
        result.invitation.expires_at = timezone.now() - timedelta(seconds=1)
        result.invitation.save(update_fields=("expires_at", "updated_at"))

        with self.assertRaises(ValidationError):
            accept_membership_invitation(
                token=result.setup_token,
                phone_number="+212600000403",
                password="NewStrongPassword!2026",
            )

        result.invitation.refresh_from_db()
        self.assertEqual(
            result.invitation.status,
            MembershipInvitationStatus.EXPIRED,
        )

    def test_creation_requires_hr_permission(self):
        with self.assertRaises(PermissionDenied):
            create_membership_invitation(
                **self.invitation_data(created_by=self.ordinary_user)
            )

    def test_active_existing_account_uses_different_workflow(self):
        User.objects.create_user(
            email="invited-member@example.com",
            first_name="Existing",
            last_name="Account",
            phone_number="+212600000405",
            password="StrongPassword!2026",
        )

        with self.assertRaises(ValidationError):
            create_membership_invitation(**self.invitation_data())


class MembershipInvitationApiTests(
    MembershipInvitationDataMixin,
    APITestCase,
):
    @classmethod
    def setUpTestData(cls):
        cls.create_common_data()

    def create_payload(self):
        return {
            "email": "api-invited@example.com",
            "first_name": "Invited",
            "last_name": "Member",
            "department_id": str(self.department.id),
            "position_id": str(self.position.id),
        }

    @override_settings(
        DEBUG=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PUBLIC_WEB_URL="https://members.askforsuccess.example",
    )
    def test_api_emails_invitation_and_sets_up_account(self):
        self.client.force_authenticate(self.hr_manager)
        creation = self.client.post(
            "/api/v1/memberships/invitations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(creation.status_code, status.HTTP_201_CREATED)
        self.assertIn("setup_token", creation.data)
        self.assertEqual(
            creation.data["email_delivery_status"],
            InvitationEmailStatus.SENT,
        )
        self.assertIsNotNone(creation.data["email_sent_at"])
        self.assertEqual(creation.data["email_error"], "")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["api-invited@example.com"])
        self.assertIn(
            "https://members.askforsuccess.example/"
            "membership/invitation/setup?token=",
            mail.outbox[0].body,
        )
        self.assertIn(creation.data["setup_token"], mail.outbox[0].body)

        self.client.force_authenticate(user=None)
        acceptance = self.client.post(
            "/api/v1/memberships/invitations/accept/",
            {
                "token": creation.data["setup_token"],
                "phone_number": "+212600000406",
                "password": "NewStrongPassword!2026",
                "password_confirmation": "NewStrongPassword!2026",
            },
            format="json",
        )
        self.assertEqual(acceptance.status_code, status.HTTP_204_NO_CONTENT)

        login = self.client.post(
            "/api/v1/auth/login/",
            {
                "email": "api-invited@example.com",
                "password": "NewStrongPassword!2026",
            },
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    @override_settings(DEBUG=True)
    @patch(
        "apps.memberships.operations.EmailMessage.send",
        side_effect=RuntimeError("Email service unavailable"),
    )
    def test_email_failure_does_not_rollback_invitation(self, mocked_send):
        self.client.force_authenticate(self.hr_manager)

        response = self.client.post(
            "/api/v1/memberships/invitations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["email_delivery_status"],
            InvitationEmailStatus.FAILED,
        )
        self.assertIn("Email service unavailable", response.data["email_error"])
        invitation = MembershipInvitation.objects.get(
            id=response.data["invitation_id"]
        )
        self.assertEqual(invitation.status, MembershipInvitationStatus.ACTIVE)
        self.assertEqual(
            invitation.email_delivery_status,
            InvitationEmailStatus.FAILED,
        )
        self.assertIsNone(invitation.email_sent_at)
        mocked_send.assert_called_once_with(fail_silently=False)

    @override_settings(
        DEBUG=False,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_production_response_never_exposes_raw_setup_token(self):
        self.client.force_authenticate(self.hr_manager)

        response = self.client.post(
            "/api/v1/memberships/invitations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("setup_token", response.data)
        self.assertEqual(
            response.data["email_delivery_status"],
            InvitationEmailStatus.SENT,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            "/membership/invitation/setup?token=",
            mail.outbox[0].body,
        )

    def test_api_rejects_unauthorized_creator(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.post(
            "/api/v1/memberships/invitations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schema_documents_english_fields(self):
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        operation = response.data["paths"][
            "/api/v1/memberships/invitations/"
        ]["post"]
        reference = operation["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        component_name = reference.rsplit("/", 1)[-1]
        schema = response.data["components"]["schemas"][component_name]
        self.assertTrue(
            {
                "email",
                "first_name",
                "last_name",
                "department_id",
                "position_id",
            }.issubset(set(schema["required"]))
        )
