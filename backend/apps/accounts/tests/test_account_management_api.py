from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    AccountInvitation,
    AccountInvitationEmailStatus,
    AccountInvitationStatus,
    User,
)
from apps.accounts.roles import ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER
from apps.audit.models import AuditAction, AuditRecord


@override_settings(DEBUG=True)
class AccountManagementApiTests(APITestCase):
    accounts_url = "/api/v1/account-management/accounts/"
    accept_url = "/api/v1/account-management/invitations/accept/"
    schema_url = "/api/schema/"

    @classmethod
    def setUpTestData(cls):
        cls.administrator = User.objects.create_user(
            email="account-admin@example.com",
            first_name="Account",
            last_name="Administrator",
            phone_number="+212600009001",
            password="StrongPassword!2026",
        )
        cls.administrator.groups.add(
            Group.objects.get(name=ACCOUNT_ADMINISTRATOR)
        )
        cls.regular_user = User.objects.create_user(
            email="regular-account@example.com",
            first_name="Regular",
            last_name="Account",
            phone_number="+212600009002",
            password="StrongPassword!2026",
        )
        cls.superuser = User.objects.create_superuser(
            email="protected-superuser@example.com",
            first_name="Protected",
            last_name="Superuser",
            phone_number="+212600009003",
            password="StrongPassword!2026",
        )

    def creation_payload(self, **overrides):
        payload = {
            "email": "new-manager@example.com",
            "first_name": "New",
            "last_name": "Manager",
            "phone_number": "+212600009010",
            "grant_hr_access": True,
        }
        payload.update(overrides)
        return payload

    def detail_url(self, user):
        return f"{self.accounts_url}{user.id}/"

    def deactivate_url(self, user):
        return f"{self.detail_url(user)}deactivate/"

    def activate_url(self, user):
        return f"{self.detail_url(user)}activate/"

    @patch("apps.accounts.account_management.EmailMessage.send", return_value=1)
    def test_administrator_creates_invited_content_manager(self, mocked_send):
        self.client.force_authenticate(self.administrator)

        response = self.client.post(
            self.accounts_url,
            self.creation_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        account = User.objects.get(email="new-manager@example.com")
        invitation = AccountInvitation.objects.get(user=account)
        self.assertFalse(account.is_active)
        self.assertFalse(account.has_usable_password())
        self.assertTrue(account.groups.filter(name=CONTENT_MANAGER).exists())
        self.assertTrue(
            account.user_permissions.filter(codename="manage_hr").exists()
        )
        self.assertEqual(invitation.status, AccountInvitationStatus.ACTIVE)
        self.assertEqual(
            invitation.email_delivery_status,
            AccountInvitationEmailStatus.SENT,
        )
        self.assertIn("setup_token", response.data)
        self.assertEqual(response.data["account"]["email"], account.email)
        mocked_send.assert_called_once_with(fail_silently=False)
        audit = AuditRecord.objects.get(
            action=AuditAction.ACCOUNT_INVITATION_CREATED,
            target_id=account.id,
        )
        self.assertEqual(audit.actor, self.administrator)
        self.assertTrue(audit.new_state["content_manager_access"])
        self.assertTrue(audit.new_state["hr_access"])

    def test_regular_user_cannot_manage_accounts(self):
        self.client.force_authenticate(self.regular_user)

        list_response = self.client.get(self.accounts_url)
        create_response = self.client.post(
            self.accounts_url,
            self.creation_payload(),
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creation_rejects_duplicate_email_and_phone(self):
        self.client.force_authenticate(self.administrator)

        email_response = self.client.post(
            self.accounts_url,
            self.creation_payload(email=self.regular_user.email),
            format="json",
        )
        phone_response = self.client.post(
            self.accounts_url,
            self.creation_payload(phone_number=self.regular_user.phone_number),
            format="json",
        )

        self.assertEqual(email_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", email_response.data)
        self.assertEqual(phone_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", phone_response.data)

    @patch("apps.accounts.account_management.EmailMessage.send", return_value=1)
    def test_invited_person_sets_password_and_activates_account(self, mocked_send):
        self.client.force_authenticate(self.administrator)
        creation = self.client.post(
            self.accounts_url,
            self.creation_payload(),
            format="json",
        )
        setup_token = creation.data["setup_token"]
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.accept_url,
            {
                "token": setup_token,
                "password": "NewStrongPassword!2026",
                "password_confirmation": "NewStrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        account = User.objects.get(email="new-manager@example.com")
        invitation = AccountInvitation.objects.get(user=account)
        self.assertTrue(account.is_active)
        self.assertTrue(account.check_password("NewStrongPassword!2026"))
        self.assertTrue(account.has_perm("accounts.manage_content"))
        self.assertTrue(account.has_perm("accounts.manage_hr"))
        self.assertEqual(invitation.status, AccountInvitationStatus.USED)
        self.assertTrue(
            AuditRecord.objects.filter(
                action=AuditAction.ACCOUNT_INVITATION_ACCEPTED,
                actor=account,
                target_id=account.id,
            ).exists()
        )

    @patch("apps.accounts.account_management.EmailMessage.send", return_value=1)
    def test_expired_invitation_is_rejected_and_marked(self, mocked_send):
        self.client.force_authenticate(self.administrator)
        creation = self.client.post(
            self.accounts_url,
            self.creation_payload(),
            format="json",
        )
        invitation = AccountInvitation.objects.get(
            user__email="new-manager@example.com"
        )
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=("expires_at", "updated_at"))
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.accept_url,
            {
                "token": creation.data["setup_token"],
                "password": "NewStrongPassword!2026",
                "password_confirmation": "NewStrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, AccountInvitationStatus.EXPIRED)

    def test_administrator_searches_and_filters_accounts(self):
        content_manager = User.objects.create_user(
            email="search-manager@example.com",
            first_name="Searchable",
            last_name="Manager",
            phone_number="+212600009020",
            password="StrongPassword!2026",
        )
        content_manager.groups.add(Group.objects.get(name=CONTENT_MANAGER))
        self.client.force_authenticate(self.administrator)

        search_response = self.client.get(
            self.accounts_url,
            {"search": "Searchable"},
        )
        role_response = self.client.get(
            self.accounts_url,
            {"role": CONTENT_MANAGER, "is_active": "true"},
        )

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            search_response.data["count"],
            1,
            search_response.data,
        )
        self.assertEqual(
            search_response.data["results"][0]["id"],
            str(content_manager.id),
        )
        self.assertEqual(role_response.status_code, status.HTTP_200_OK)
        self.assertIn(
            str(content_manager.id),
            [item["id"] for item in role_response.data["results"]],
        )

    def test_deactivation_blocks_account_and_removes_access(self):
        target = User.objects.create_user(
            email="departing-manager@example.com",
            first_name="Departing",
            last_name="Manager",
            phone_number="+212600009030",
            password="StrongPassword!2026",
            is_staff=True,
        )
        target.groups.add(
            Group.objects.get(name=CONTENT_MANAGER),
            Group.objects.create(name="temporary_project_role"),
        )
        target.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        refresh = RefreshToken.for_user(target)
        self.client.force_authenticate(self.administrator)

        response = self.client.post(
            self.deactivate_url(target),
            {"reason": "The person left the association."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.assertFalse(target.is_staff)
        self.assertFalse(target.has_usable_password())
        self.assertFalse(target.groups.exists())
        self.assertFalse(target.user_permissions.exists())
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )
        audit = AuditRecord.objects.get(
            action=AuditAction.ACCOUNT_DEACTIVATED,
            target_id=target.id,
        )
        self.assertEqual(audit.reason, "The person left the association.")
        self.assertTrue(audit.previous_state["content_manager_access"])
        self.assertFalse(audit.new_state["account_active"])

    def test_administrator_cannot_deactivate_self_or_superuser(self):
        self.client.force_authenticate(self.administrator)

        self_response = self.client.post(
            self.deactivate_url(self.administrator),
            {"reason": "Not allowed."},
            format="json",
        )
        superuser_response = self.client.post(
            self.deactivate_url(self.superuser),
            {"reason": "Not allowed."},
            format="json",
        )

        self.assertEqual(self_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(superuser_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.administrator.refresh_from_db()
        self.superuser.refresh_from_db()
        self.assertTrue(self.administrator.is_active)
        self.assertTrue(self.superuser.is_active)

    @patch("apps.accounts.account_management.EmailMessage.send", return_value=1)
    def test_reactivation_requires_new_setup_and_does_not_restore_roles(
        self,
        mocked_send,
    ):
        target = User.objects.create_user(
            email="returning-manager@example.com",
            first_name="Returning",
            last_name="Manager",
            phone_number="+212600009040",
            password="StrongPassword!2026",
        )
        target.groups.add(Group.objects.get(name=CONTENT_MANAGER))
        self.client.force_authenticate(self.administrator)
        self.client.post(
            self.deactivate_url(target),
            {"reason": "Temporary departure."},
            format="json",
        )

        invitation_response = self.client.post(
            self.activate_url(target),
            {"reason": "The person returned to the association."},
            format="json",
        )

        self.assertEqual(invitation_response.status_code, status.HTTP_201_CREATED)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.assertFalse(target.groups.exists())
        self.client.force_authenticate(user=None)
        acceptance = self.client.post(
            self.accept_url,
            {
                "token": invitation_response.data["setup_token"],
                "password": "ReturningPassword!2026",
                "password_confirmation": "ReturningPassword!2026",
            },
            format="json",
        )
        self.assertEqual(acceptance.status_code, status.HTTP_204_NO_CONTENT)
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertFalse(target.groups.exists())

    def test_access_changes_have_explicit_audit_state(self):
        self.client.force_authenticate(self.administrator)

        response = self.client.put(
            f"/api/v1/access/users/{self.regular_user.id}/",
            {
                "roles": [CONTENT_MANAGER],
                "permissions": ["accounts.manage_hr"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit = AuditRecord.objects.get(
            action=AuditAction.ACCESS_ASSIGNMENT_CHANGED,
            target_id=self.regular_user.id,
        )
        self.assertFalse(audit.previous_state["content_manager_access"])
        self.assertTrue(audit.new_state["content_manager_access"])
        self.assertTrue(audit.new_state["hr_access"])

    def test_openapi_schema_contains_account_management_endpoints(self):
        response = self.client.get(self.schema_url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_paths = {
            "/api/v1/account-management/accounts/",
            "/api/v1/account-management/accounts/{user_id}/",
            "/api/v1/account-management/accounts/{user_id}/deactivate/",
            "/api/v1/account-management/accounts/{user_id}/activate/",
            "/api/v1/account-management/invitations/accept/",
        }
        self.assertTrue(expected_paths.issubset(response.data["paths"]))
