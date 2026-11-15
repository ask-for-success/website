from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User


class AuthenticationApiTests(APITestCase):
    register_url = "/api/v1/auth/register/"
    login_url = "/api/v1/auth/login/"
    refresh_url = "/api/v1/auth/refresh/"
    logout_url = "/api/v1/auth/logout/"
    me_url = "/api/v1/auth/me/"
    password_url = "/api/v1/auth/password/"
    schema_url = "/api/schema/"
    swagger_url = "/api/docs/"
    redoc_url = "/api/redoc/"

    def registration_data(self, **overrides):
        data = {
            "email": "person@example.com",
            "first_name": "Ikram",
            "last_name": "Manager",
            "phone_number": "+212600000001",
            "password": "StrongPassword!2026",
            "password_confirmation": "StrongPassword!2026",
        }
        data.update(overrides)
        return data

    def register(self, **overrides):
        return self.client.post(
            self.register_url,
            self.registration_data(**overrides),
            format="json",
        )

    def authorize(self, access_token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_registration_creates_user_and_tokens(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data["user"]["email"], "person@example.com")

        user = User.objects.get(email="person@example.com")
        self.assertTrue(user.check_password("StrongPassword!2026"))

    def test_registration_rejects_case_insensitive_duplicate_email(self):
        self.register()

        response = self.register(
            email="PERSON@EXAMPLE.COM",
            phone_number="+212600000002",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_rejects_duplicate_phone_number(self):
        self.register()

        response = self.register(email="another@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_registration_requires_phone_number(self):
        data = self.registration_data()
        data.pop("phone_number")

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_login_accepts_case_insensitive_email(self):
        self.register()

        response = self.client.post(
            self.login_url,
            {
                "email": "PERSON@EXAMPLE.COM",
                "password": "StrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_login_rejects_inactive_user(self):
        self.register()
        user = User.objects.get(email="person@example.com")
        user.is_active = False
        user.save(update_fields=("is_active",))

        response = self.client.post(
            self.login_url,
            {
                "email": "person@example.com",
                "password": "StrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        registration = self.register()
        self.authorize(registration.data["access_token"])

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "person@example.com")

    def test_profile_update(self):
        registration = self.register()
        self.authorize(registration.data["access_token"])

        response = self.client.patch(
            self.me_url,
            {
                "first_name": "Updated name",
                "phone_number": "+212600000009",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated name")
        self.assertEqual(response.data["phone_number"], "+212600000009")

    def test_profile_update_rejects_login_email_change(self):
        registration = self.register()
        self.authorize(registration.data["access_token"])

        response = self.client.patch(
            self.me_url,
            {"email": "changed@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        user = User.objects.get(id=registration.data["user"]["id"])
        self.assertEqual(user.email, "person@example.com")

    def test_refresh_rotates_tokens_and_revokes_previous_refresh_token(self):
        registration = self.register()
        old_refresh_token = registration.data["refresh_token"]

        response = self.client.post(
            self.refresh_url,
            {"refresh_token": old_refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

        reused_response = self.client.post(
            self.refresh_url,
            {"refresh_token": old_refresh_token},
            format="json",
        )
        self.assertEqual(reused_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_revokes_refresh_token(self):
        registration = self.register()
        self.authorize(registration.data["access_token"])
        refresh_token = registration.data["refresh_token"]

        response = self.client.post(
            self.logout_url,
            {"refresh_token": refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.client.credentials()
        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh_token": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_revokes_existing_tokens(self):
        registration = self.register()
        self.authorize(registration.data["access_token"])

        response = self.client.post(
            self.password_url,
            {
                "current_password": "StrongPassword!2026",
                "new_password": "NewStrongPassword!2026",
                "new_password_confirmation": "NewStrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        old_access_response = self.client.get(self.me_url)
        self.assertEqual(old_access_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials()
        old_login_response = self.client.post(
            self.login_url,
            {
                "email": "person@example.com",
                "password": "StrongPassword!2026",
            },
            format="json",
        )
        self.assertEqual(old_login_response.status_code, status.HTTP_400_BAD_REQUEST)

        new_login_response = self.client.post(
            self.login_url,
            {
                "email": "person@example.com",
                "password": "NewStrongPassword!2026",
            },
            format="json",
        )
        self.assertEqual(new_login_response.status_code, status.HTTP_200_OK)

    def test_openapi_schema_contains_authentication_endpoints(self):
        response = self.client.get(self.schema_url, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/auth/register/", response.data["paths"])
        self.assertIn("/api/v1/auth/login/", response.data["paths"])
        self.assertIn("/api/v1/auth/me/", response.data["paths"])

        register_operation = response.data["paths"]["/api/v1/auth/register/"]["post"]
        self.assertEqual(register_operation["tags"], ["Authentication"])
        self.assertIn("requestBody", register_operation)

        request_reference = register_operation["requestBody"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        component_name = request_reference.rsplit("/", 1)[-1]
        register_schema = response.data["components"]["schemas"][component_name]
        self.assertEqual(
            set(register_schema["required"]),
            {
                "email",
                "first_name",
                "last_name",
                "phone_number",
                "password",
                "password_confirmation",
            },
        )

        security_schema = response.data["components"]["securitySchemes"]["jwtAuth"]
        self.assertEqual(security_schema["type"], "http")
        self.assertEqual(security_schema["scheme"], "bearer")

    def test_swagger_ui_is_publicly_available(self):
        response = self.client.get(self.swagger_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "SwaggerUIBundle")

    def test_redoc_is_publicly_available(self):
        response = self.client.get(self.redoc_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "redoc")
