from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.roles import ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER


class AccessControlApiTests(APITestCase):
    current_access_url = "/api/v1/access/me/"
    access_options_url = "/api/v1/access/options/"
    schema_url = "/api/schema/"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="user@example.com",
            first_name="Regular",
            last_name="User",
            phone_number="+212600000101",
            password="StrongPassword!2026",
        )
        cls.access_manager = User.objects.create_user(
            email="manager@example.com",
            first_name="Access",
            last_name="Manager",
            phone_number="+212600000102",
            password="StrongPassword!2026",
        )
        cls.target_user = User.objects.create_user(
            email="target@example.com",
            first_name="Target",
            last_name="User",
            phone_number="+212600000103",
            password="StrongPassword!2026",
        )
        cls.access_manager.groups.add(
            Group.objects.get(name=ACCOUNT_ADMINISTRATOR)
        )

    def assignment_url(self, user):
        return f"/api/v1/access/users/{user.id}/"

    def test_system_roles_and_individual_hr_permission_exist(self):
        account_administrator = Group.objects.get(name=ACCOUNT_ADMINISTRATOR)
        content_manager = Group.objects.get(name=CONTENT_MANAGER)
        hr_permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="manage_hr",
        )

        self.assertSetEqual(
            set(account_administrator.permissions.values_list("codename", flat=True)),
            {"manage_accounts", "manage_access_assignments", "view_audit_log"},
        )
        self.assertSetEqual(
            set(content_manager.permissions.values_list("codename", flat=True)),
            {"manage_content"},
        )
        self.assertFalse(Group.objects.filter(name="hr_manager").exists())
        self.assertFalse(hr_permission.group_set.exists())

    def test_current_access_requires_authentication(self):
        response = self.client.get(self.current_access_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_access_returns_content_role_and_direct_hr_permission(self):
        self.user.groups.add(Group.objects.get(name=CONTENT_MANAGER))
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(self.current_access_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["roles"], [CONTENT_MANAGER])
        self.assertEqual(
            response.data["permissions"],
            ["accounts.manage_content", "accounts.manage_hr"],
        )
        self.assertFalse(response.data["is_staff"])
        self.assertFalse(response.data["is_superuser"])

    def test_regular_user_cannot_read_options_or_manage_access(self):
        self.client.force_authenticate(self.user)

        options_response = self.client.get(self.access_options_url)
        assignment_response = self.client.put(
            self.assignment_url(self.target_user),
            {"roles": [CONTENT_MANAGER], "permissions": []},
            format="json",
        )

        self.assertEqual(options_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(assignment_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_access_manager_can_list_roles_and_additional_permissions(self):
        self.client.force_authenticate(self.access_manager)

        response = self.client.get(self.access_options_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [role["key"] for role in response.data["roles"]],
            [ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER],
        )
        self.assertEqual(
            response.data["additional_permissions"],
            [
                {
                    "key": "accounts.manage_hr",
                    "description": (
                        "Allows a content manager to manage recruitment and official "
                        "membership records."
                    ),
                    "requires_role": CONTENT_MANAGER,
                }
            ],
        )

    def test_access_manager_can_read_and_replace_managed_access(self):
        custom_group = Group.objects.create(name="project_specific_group")
        unrelated_permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="add_user",
        )
        self.target_user.groups.add(custom_group)
        self.target_user.user_permissions.add(unrelated_permission)
        self.client.force_authenticate(self.access_manager)

        response = self.client.put(
            self.assignment_url(self.target_user),
            {
                "roles": [CONTENT_MANAGER, ACCOUNT_ADMINISTRATOR],
                "permissions": ["accounts.manage_hr"],
            },
            format="json",
        )
        read_response = self.client.get(self.assignment_url(self.target_user))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["roles"],
            [ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER],
        )
        self.assertEqual(
            response.data["direct_permissions"],
            ["accounts.manage_hr"],
        )
        self.assertIn("accounts.manage_content", response.data["permissions"])
        self.assertIn("accounts.manage_hr", response.data["permissions"])
        self.assertTrue(self.target_user.groups.filter(id=custom_group.id).exists())
        self.assertTrue(
            self.target_user.user_permissions.filter(id=unrelated_permission.id).exists()
        )

    def test_hr_permission_requires_content_manager_role(self):
        self.client.force_authenticate(self.access_manager)

        response = self.client.put(
            self.assignment_url(self.target_user),
            {
                "roles": [ACCOUNT_ADMINISTRATOR],
                "permissions": ["accounts.manage_hr"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("permissions", response.data)

    def test_assignment_rejects_unknown_and_duplicate_values(self):
        self.client.force_authenticate(self.access_manager)

        unknown_response = self.client.put(
            self.assignment_url(self.target_user),
            {"roles": ["unknown_role"], "permissions": []},
            format="json",
        )
        duplicate_response = self.client.put(
            self.assignment_url(self.target_user),
            {
                "roles": [CONTENT_MANAGER, CONTENT_MANAGER],
                "permissions": [],
            },
            format="json",
        )

        self.assertEqual(unknown_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_superuser_cannot_change_own_access(self):
        self.client.force_authenticate(self.access_manager)

        response = self.client.put(
            self.assignment_url(self.access_manager),
            {"roles": [], "permissions": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            self.access_manager.groups.filter(name=ACCOUNT_ADMINISTRATOR).exists()
        )

    def test_superuser_can_bootstrap_access_assignments(self):
        superuser = User.objects.create_superuser(
            email="superuser@example.com",
            first_name="System",
            last_name="Administrator",
            phone_number="+212600000104",
            password="StrongPassword!2026",
        )
        self.client.force_authenticate(superuser)

        response = self.client.put(
            self.assignment_url(self.target_user),
            {
                "roles": [CONTENT_MANAGER],
                "permissions": ["accounts.manage_hr"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["roles"], [CONTENT_MANAGER])
        self.assertEqual(
            response.data["direct_permissions"],
            ["accounts.manage_hr"],
        )

    def test_openapi_schema_contains_access_control_endpoints(self):
        response = self.client.get(self.schema_url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/access/me/", response.data["paths"])
        self.assertIn("/api/v1/access/options/", response.data["paths"])
        self.assertIn(
            "/api/v1/access/users/{user_id}/",
            response.data["paths"],
        )
        self.assertEqual(
            response.data["paths"]["/api/v1/access/me/"]["get"]["tags"],
            ["Access control"],
        )
