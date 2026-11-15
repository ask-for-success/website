from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from ..models import (
    AcknowledgementEmailStatus,
    DonationSubmission,
    DonationType,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class DonationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.content_manager = User.objects.create_user(
            email="donation-manager@example.com",
            first_name="Donation",
            last_name="Manager",
            phone_number="+212600000801",
            password="StrongPassword!2026",
        )
        cls.content_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.ordinary_user = User.objects.create_user(
            email="donation-user@example.com",
            first_name="Ordinary",
            last_name="User",
            phone_number="+212600000802",
            password="StrongPassword!2026",
        )

    def submission_payload(self, **overrides):
        payload = {
            "first_name": "  Jane  ",
            "last_name": "  Donor  ",
            "email": "JANE.DONOR@example.com",
            "phone_number": "  +212600000803  ",
            "donation_type": DonationType.CASH,
            "details": "  I would like to support the next workshop.  ",
        }
        payload.update(overrides)
        return payload

    def create_submission(self, **overrides):
        return self.client.post(
            "/api/v1/donations/submissions/",
            self.submission_payload(**overrides),
            format="json",
        )

    def test_public_fixed_form_records_submission_and_sends_acknowledgement(self):
        response = self.create_submission()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["donation_type"], DonationType.CASH)
        self.assertEqual(
            response.data["acknowledgement_email_status"],
            AcknowledgementEmailStatus.SENT,
        )
        self.assertNotIn("email", response.data)
        self.assertNotIn("phone_number", response.data)
        self.assertNotIn("details", response.data)

        submission = DonationSubmission.objects.get(pk=response.data["id"])
        self.assertEqual(submission.first_name, "Jane")
        self.assertEqual(submission.last_name, "Donor")
        self.assertEqual(submission.email, "jane.donor@example.com")
        self.assertEqual(submission.phone_number, "+212600000803")
        self.assertEqual(
            submission.details,
            "I would like to support the next workshop.",
        )
        self.assertIsNotNone(submission.acknowledgement_email_sent_at)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["jane.donor@example.com"])
        self.assertIn("cash donation", mail.outbox[0].body)
        self.assertIn("our team will contact you later", mail.outbox[0].body)

    def test_public_form_requires_one_of_the_fixed_donation_types(self):
        response = self.create_submission(donation_type="cryptocurrency")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("donation_type", response.data)
        self.assertFalse(DonationSubmission.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_public_form_requires_contact_and_donation_details(self):
        response = self.create_submission(phone_number=" ", details=" ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)
        self.assertIn("details", response.data)
        self.assertFalse(DonationSubmission.objects.exists())

    @patch(
        "apps.donations.operations.EmailMessage.send",
        side_effect=RuntimeError("Email provider unavailable"),
    )
    def test_email_failure_does_not_delete_submission(self, mocked_send):
        response = self.create_submission(donation_type=DonationType.GOODS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["acknowledgement_email_status"],
            AcknowledgementEmailStatus.FAILED,
        )
        submission = DonationSubmission.objects.get(pk=response.data["id"])
        self.assertEqual(
            submission.acknowledgement_email_status,
            AcknowledgementEmailStatus.FAILED,
        )
        self.assertIn(
            "Email provider unavailable",
            submission.acknowledgement_email_error,
        )
        mocked_send.assert_called_once()

    def test_only_content_managers_can_list_donor_data(self):
        creation = self.create_submission()

        anonymous = self.client.get("/api/v1/donations/management/submissions/")
        self.client.force_authenticate(self.ordinary_user)
        ordinary = self.client.get("/api/v1/donations/management/submissions/")
        self.client.force_authenticate(self.content_manager)
        manager = self.client.get("/api/v1/donations/management/submissions/")

        self.assertEqual(creation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(ordinary.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(manager.status_code, status.HTTP_200_OK)
        self.assertEqual(manager.data["count"], 1)
        self.assertEqual(
            manager.data["results"][0]["email"],
            "jane.donor@example.com",
        )

    def test_content_manager_can_filter_search_and_open_submission(self):
        cash = self.create_submission()
        goods = self.create_submission(
            first_name="Adam",
            last_name="Supporter",
            email="adam@example.com",
            phone_number="+212600000804",
            donation_type=DonationType.GOODS,
            details="Books and school supplies.",
        )
        self.client.force_authenticate(self.content_manager)

        filtered = self.client.get(
            "/api/v1/donations/management/submissions/",
            {"donation_type": DonationType.GOODS, "search": "Adam"},
        )
        detail = self.client.get(
            f"/api/v1/donations/management/submissions/{goods.data['id']}/"
        )

        self.assertEqual(cash.status_code, status.HTTP_201_CREATED)
        self.assertEqual(goods.status_code, status.HTTP_201_CREATED)
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["id"], goods.data["id"])
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["details"], "Books and school supplies.")

    def test_schema_documents_donation_routes(self):
        response = self.client.get("/api/schema/")
        schema = response.content.decode()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/donations/submissions/", schema)
        self.assertIn("/api/v1/donations/management/submissions/", schema)

