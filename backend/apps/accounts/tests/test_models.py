from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User


class UserModelTests(TestCase):
    def valid_user_data(self, **overrides):
        data = {
            "email": "person@example.com",
            "password": "strong-test-password",
            "first_name": "Ikram",
            "last_name": "Manager",
            "phone_number": "+212600000001",
        }
        data.update(overrides)
        return data

    def test_user_has_uuid_primary_key(self):
        user = User.objects.create_user(**self.valid_user_data())

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "person@example.com")
        self.assertTrue(user.check_password("strong-test-password"))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_email_is_required(self):
        with self.assertRaisesMessage(ValueError, "Email is required."):
            User.objects.create_user(**self.valid_user_data(email=""))

    def test_email_is_unique_case_insensitively(self):
        User.objects.create_user(**self.valid_user_data())

        with self.assertRaises(ValidationError):
            User.objects.create_user(
                **self.valid_user_data(
                    email="PERSON@example.com",
                    phone_number="+212600000002",
                )
            )

    def test_email_login_is_case_insensitive(self):
        user = User.objects.create_user(**self.valid_user_data())

        authenticated_user = authenticate(
            username="PERSON@EXAMPLE.COM",
            password="strong-test-password",
        )

        self.assertEqual(authenticated_user, user)

    def test_phone_number_is_unique(self):
        User.objects.create_user(**self.valid_user_data())

        with self.assertRaises(ValidationError):
            User.objects.create_user(
                **self.valid_user_data(email="another@example.com")
            )

    def test_phone_number_is_required(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(**self.valid_user_data(phone_number=""))

    def test_first_and_last_names_are_stored_separately(self):
        user = User.objects.create_user(**self.valid_user_data())

        self.assertEqual(user.first_name, "Ikram")
        self.assertEqual(user.last_name, "Manager")
        self.assertFalse(hasattr(user, "full_name"))

    def test_national_id_is_not_on_user_model(self):
        field_names = {field.name for field in User._meta.get_fields()}

        self.assertNotIn("national_id_number", field_names)
        self.assertNotIn("cin", field_names)
        self.assertNotIn("cni", field_names)

    def test_email_verification_field_does_not_exist(self):
        field_names = {field.name for field in User._meta.get_fields()}

        self.assertNotIn("email_verified", field_names)
        self.assertNotIn("is_email_verified", field_names)

    def test_superuser_creation(self):
        superuser = User.objects.create_superuser(**self.valid_user_data())

        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
