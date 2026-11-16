import base64
import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.audit.models import AuditAction, AuditDomain
from apps.content.models import (
    ContentCategory,
    ContentSection,
    NewsArticle,
    PublicationStatus as ContentPublicationStatus,
)
from apps.donations.models import (
    AcknowledgementEmailStatus,
    DonationSubmission,
    DonationType,
)
from apps.events.models import (
    Event,
    EventQuestionType,
    EventRegistration,
    PublicationStatus as EventPublicationStatus,
)
from apps.events.operations import rebuild_qr_code
from apps.memberships.models import Membership, MembershipStatus
from apps.organization.models import Department, Position
from apps.recruitment.models import (
    ApplicationCv,
    ApplicationStatus,
    OfferResponse,
    RecruitmentFormStatus,
    RecruitmentQuestionType,
)


TINY_GIF = base64.b64decode(
    "R0lGODlhAQABAIABAP///wAAACwAAAAAAQABAAACAkQBADs="
)


def image_file(name="acceptance-image.gif"):
    return SimpleUploadedFile(name, TINY_GIF, content_type="image/gif")


def pdf_file(name="acceptance-cv.pdf"):
    return SimpleUploadedFile(
        name,
        b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF",
        content_type="application/pdf",
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class BackendWorkflowAcceptanceTests(APITestCase):
    password = "StrongPassword!2026"

    @classmethod
    def setUpClass(cls):
        cls.storage_directory = TemporaryDirectory()
        storage_root = Path(cls.storage_directory.name)
        cls.public_storage_directory = storage_root / "public"
        cls.private_storage_directory = storage_root / "private"
        cls.public_storage_directory.mkdir()
        cls.private_storage_directory.mkdir()
        cls.storage_override = override_settings(
            MEDIA_URL="/acceptance-media/",
            MEDIA_ROOT=cls.public_storage_directory,
            PRIVATE_MEDIA_ROOT=cls.private_storage_directory,
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {
                        "location": cls.public_storage_directory,
                        "base_url": "/acceptance-media/",
                    },
                },
                "private": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {
                        "location": cls.private_storage_directory,
                        "base_url": None,
                    },
                },
                "staticfiles": {
                    "BACKEND": (
                        "django.contrib.staticfiles.storage."
                        "StaticFilesStorage"
                    ),
                },
            },
        )
        cls.storage_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.storage_override.disable()
        cls.storage_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.account_administrator = User.objects.create_user(
            email="acceptance-admin@example.com",
            first_name="Acceptance",
            last_name="Administrator",
            phone_number="+212600009001",
            password=cls.password,
        )
        cls.account_administrator.groups.add(
            Group.objects.get(name="account_administrator")
        )
        cls.hr_manager = User.objects.create_user(
            email="acceptance-manager@example.com",
            first_name="Acceptance",
            last_name="Manager",
            phone_number="+212600009002",
            password=cls.password,
        )
        cls.hr_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.hr_manager.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )
        cls.scanner_user = User.objects.create_user(
            email="acceptance-scanner@example.com",
            first_name="Acceptance",
            last_name="Scanner",
            phone_number="+212600009003",
            password=cls.password,
        )
        cls.scanner_membership = Membership.objects.create(
            user=cls.scanner_user,
            status=MembershipStatus.ACTIVE,
        )
        cls.department = Department.objects.create(
            name="Acceptance Engineering",
            description="Builds and maintains association systems.",
        )
        cls.position = Position.objects.create(
            department=cls.department,
            name="Acceptance Backend Developer",
            description="Develops backend services.",
        )

    def authenticated_client(self, user):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}"
        )
        return client

    def register_candidate(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "email": "acceptance-candidate@example.com",
                "first_name": "Acceptance",
                "last_name": "Candidate",
                "phone_number": "+212600009004",
                "password": self.password,
                "password_confirmation": self.password,
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}"
        )
        return client, User.objects.get(pk=response.data["user"]["id"])

    def actor_timeline(self, actor):
        administrator = self.authenticated_client(self.account_administrator)
        actor_search = administrator.get(
            "/api/v1/audit/actors/",
            {"search": actor.email},
        )
        self.assertEqual(
            actor_search.status_code,
            status.HTTP_200_OK,
            actor_search.data,
        )
        self.assertEqual(actor_search.data["count"], 1)
        self.assertEqual(
            actor_search.data["results"][0]["id"],
            str(actor.id),
        )
        timeline = administrator.get(
            f"/api/v1/audit/actors/{actor.id}/records/",
            {"page_size": 100},
        )
        self.assertEqual(timeline.status_code, status.HTTP_200_OK, timeline.data)
        return timeline.data["results"]

    def test_recruitment_acceptance_onboarding_and_audit_journey(self):
        public_client = APIClient()
        departments = public_client.get("/api/v1/organization/departments/")
        self.assertEqual(departments.status_code, status.HTTP_200_OK)
        self.assertEqual(departments.data[0]["id"], str(self.department.id))
        self.assertEqual(
            departments.data[0]["positions"][0]["id"],
            str(self.position.id),
        )

        candidate_client, candidate = self.register_candidate()
        hr_client = self.authenticated_client(self.hr_manager)
        form_response = hr_client.post(
            "/api/v1/recruitment/forms/",
            {
                "name": "Acceptance developer application",
                "description": "Acceptance coverage for recruitment.",
                "status": RecruitmentFormStatus.ACTIVE,
                "department_id": str(self.department.id),
                "position_id": str(self.position.id),
                "questions": [
                    {
                        "label": "Why do you want to join?",
                        "question_type": RecruitmentQuestionType.LONG_TEXT,
                        "is_required": True,
                        "display_order": 1,
                        "options": [],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(
            form_response.status_code,
            status.HTTP_201_CREATED,
            form_response.data,
        )
        opportunity_response = hr_client.post(
            "/api/v1/recruitment/opportunities/",
            {
                "form_id": form_response.data["id"],
                "title": "Acceptance backend opportunity",
                "slug": "acceptance-backend-opportunity",
                "summary": "Join the acceptance engineering team.",
                "description_markdown": "## Role\n\nBuild reliable services.",
                "status": "published",
            },
            format="json",
        )
        self.assertEqual(
            opportunity_response.status_code,
            status.HTTP_201_CREATED,
            opportunity_response.data,
        )

        public_opportunity = public_client.get(
            "/api/v1/recruitment/opportunities/acceptance-backend-opportunity/"
        )
        self.assertEqual(public_opportunity.status_code, status.HTTP_200_OK)
        question_id = public_opportunity.data["application_form"]["questions"][
            0
        ]["id"]
        application_response = candidate_client.post(
            (
                "/api/v1/recruitment/opportunities/"
                f"{opportunity_response.data['id']}/applications/"
            ),
            {
                "answers": json.dumps(
                    [
                        {
                            "question_id": question_id,
                            "value": "I want to build reliable association systems.",
                        }
                    ]
                ),
                "cv": pdf_file(),
            },
            format="multipart",
        )
        self.assertEqual(
            application_response.status_code,
            status.HTTP_201_CREATED,
            application_response.data,
        )
        application_id = application_response.data["id"]
        stored_cv = ApplicationCv.objects.get(application_id=application_id)
        self.assertTrue(stored_cv.file.storage.exists(stored_cv.file.name))

        cv_path = urlsplit(
            application_response.data["cv"]["download_url"]
        ).path
        denied_cv = public_client.get(cv_path)
        self.assertEqual(denied_cv.status_code, status.HTTP_401_UNAUTHORIZED)
        candidate_cv = candidate_client.get(cv_path)
        self.assertEqual(candidate_cv.status_code, status.HTTP_200_OK)
        self.assertTrue(
            b"".join(candidate_cv.streaming_content).startswith(b"%PDF")
        )

        offer_response = hr_client.patch(
            f"/api/v1/recruitment/applications/{application_id}/status/",
            {"status": ApplicationStatus.OFFER_PENDING},
            format="json",
        )
        self.assertEqual(offer_response.status_code, status.HTTP_200_OK)
        acceptance_response = candidate_client.post(
            (
                f"/api/v1/recruitment/applications/{application_id}/"
                "offer-response/"
            ),
            {"response": OfferResponse.ACCEPT},
            format="json",
        )
        self.assertEqual(
            acceptance_response.status_code,
            status.HTTP_200_OK,
            acceptance_response.data,
        )
        self.assertEqual(
            acceptance_response.data["status"],
            ApplicationStatus.ACCEPTED,
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(
            all(message.to == [candidate.email] for message in mail.outbox)
        )

        pending_membership = candidate_client.get("/api/v1/memberships/me/")
        self.assertEqual(pending_membership.status_code, status.HTTP_200_OK)
        self.assertTrue(pending_membership.data["onboarding_required"])
        self.assertFalse(
            pending_membership.data["can_access_member_features"]
        )
        onboarding_response = candidate_client.post(
            "/api/v1/memberships/me/onboarding/",
            {"national_id_number": "AB654321"},
            format="json",
        )
        self.assertEqual(
            onboarding_response.status_code,
            status.HTTP_200_OK,
            onboarding_response.data,
        )
        self.assertTrue(onboarding_response.data["can_access_member_features"])
        self.assertFalse(onboarding_response.data["onboarding_required"])
        membership_id = onboarding_response.data["membership"]["id"]

        identity_response = hr_client.get(
            f"/api/v1/memberships/{membership_id}/identity/"
        )
        self.assertEqual(identity_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            identity_response.data["national_id_number"],
            "AB654321",
        )

        timeline = self.actor_timeline(candidate)
        actions = {record["action"] for record in timeline}
        domains = {record["domain"] for record in timeline}
        self.assertTrue(
            {
                AuditAction.ACCOUNT_REGISTERED,
                AuditAction.APPLICATION_STATUS_CHANGED,
                AuditAction.ONBOARDING_STATUS_CHANGED,
                AuditAction.NATIONAL_ID_SUBMITTED,
            }.issubset(actions)
        )
        self.assertTrue(
            {
                AuditDomain.ACCOUNTS,
                AuditDomain.RECRUITMENT,
                AuditDomain.MEMBERSHIP,
            }.issubset(domains)
        )
        hr_timeline = self.actor_timeline(self.hr_manager)
        hr_actions = {record["action"] for record in hr_timeline}
        self.assertTrue(
            {
                AuditAction.MEMBERSHIP_CREATED,
                AuditAction.NATIONAL_ID_VIEWED,
            }.issubset(hr_actions)
        )

    def test_content_event_registration_and_check_in_journey(self):
        manager_client = self.authenticated_client(self.hr_manager)
        public_client = APIClient()
        news_category = ContentCategory.objects.get(
            section=ContentSection.NEWS,
            slug="events",
        )
        article_response = manager_client.post(
            "/api/v1/content/news/",
            {
                "category": str(news_category.id),
                "title": "Acceptance community story",
                "slug": "acceptance-community-story",
                "excerpt": "A complete acceptance story.",
                "body_markdown": (
                    "## Acceptance story\n\n"
                    "This article was published through the CMS API."
                ),
                "cover_image": image_file(),
                "cover_alt_text": "Association members working together",
                "publication_status": ContentPublicationStatus.PUBLISHED,
                "is_featured": True,
                "display_order": 1,
            },
            format="multipart",
        )
        self.assertEqual(
            article_response.status_code,
            status.HTTP_201_CREATED,
            article_response.data,
        )
        article = NewsArticle.objects.get(pk=article_response.data["id"])
        self.assertTrue(article.cover_image.storage.exists(article.cover_image.name))
        public_article = public_client.get(
            "/api/v1/content/news/acceptance-community-story/"
        )
        self.assertEqual(public_article.status_code, status.HTTP_200_OK)
        self.assertIn(
            "/acceptance-media/content/news/",
            public_article.data["cover_image"],
        )

        starts_at = timezone.now() + timedelta(days=3)
        event_response = manager_client.post(
            "/api/v1/events/",
            {
                "title": "Acceptance summit",
                "summary": "Backend acceptance event.",
                "description": "A complete registration and check-in journey.",
                "location": "Casablanca",
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
                "capacity": 20,
                "publication_status": EventPublicationStatus.PUBLISHED,
                "requires_qr_code": True,
                "questions": [
                    {
                        "label": "Do you accept the event terms?",
                        "question_type": EventQuestionType.YES_NO,
                        "is_required": True,
                        "display_order": 1,
                        "options": [],
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(
            event_response.status_code,
            status.HTTP_201_CREATED,
            event_response.data,
        )
        event = Event.objects.get(pk=event_response.data["id"])
        event_question = event.questions.get()
        registration_response = public_client.post(
            f"/api/v1/events/{event.id}/registrations/",
            {
                "email": "acceptance-visitor@example.com",
                "answers": [
                    {
                        "question_id": str(event_question.id),
                        "value": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(
            registration_response.status_code,
            status.HTTP_201_CREATED,
            registration_response.data,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["acceptance-visitor@example.com"])
        self.assertEqual(mail.outbox[0].attachments[0][2], "image/png")
        registration = EventRegistration.objects.get(
            pk=registration_response.data["id"]
        )
        qr_code = rebuild_qr_code(registration.ticket)
        self.assertIsNotNone(qr_code)

        assignment_response = manager_client.post(
            f"/api/v1/events/{event.id}/scanners/",
            {"membership_id": str(self.scanner_membership.id)},
            format="json",
        )
        self.assertEqual(
            assignment_response.status_code,
            status.HTTP_201_CREATED,
            assignment_response.data,
        )
        scanner_client = self.authenticated_client(self.scanner_user)
        first_scan = scanner_client.post(
            f"/api/v1/events/{event.id}/check-ins/",
            {"qr_code": qr_code},
            format="json",
        )
        second_scan = scanner_client.post(
            f"/api/v1/events/{event.id}/check-ins/",
            {"qr_code": qr_code},
            format="json",
        )
        self.assertEqual(first_scan.status_code, status.HTTP_200_OK)
        self.assertEqual(first_scan.data["status"], "checked_in")
        self.assertEqual(second_scan.status_code, status.HTTP_200_OK)
        self.assertEqual(second_scan.data["status"], "already_checked_in")

        statistics = manager_client.get(
            f"/api/v1/events/{event.id}/statistics/"
        )
        self.assertEqual(statistics.status_code, status.HTTP_200_OK)
        self.assertEqual(statistics.data["registered_count"], 1)
        self.assertEqual(statistics.data["checked_in_count"], 1)
        self.assertEqual(statistics.data["remaining_seats"], 19)

        manager_timeline = self.actor_timeline(self.hr_manager)
        manager_domains = {record["domain"] for record in manager_timeline}
        self.assertTrue(
            {AuditDomain.CONTENT, AuditDomain.EVENTS}.issubset(manager_domains)
        )
        scanner_timeline = self.actor_timeline(self.scanner_user)
        self.assertTrue(
            any(
                record["domain"] == AuditDomain.EVENTS
                and record["action"] == AuditAction.API_ACTION_PERFORMED
                for record in scanner_timeline
            )
        )

    def test_donation_acknowledgement_and_content_manager_journey(self):
        public_client = APIClient()
        manager_client = self.authenticated_client(self.hr_manager)
        submission_response = public_client.post(
            "/api/v1/donations/submissions/",
            {
                "first_name": "Acceptance",
                "last_name": "Donor",
                "email": "acceptance-donor@example.com",
                "phone_number": "+212600009005",
                "donation_type": DonationType.GOODS,
                "details": "Books and workshop equipment.",
            },
            format="json",
        )
        self.assertEqual(
            submission_response.status_code,
            status.HTTP_201_CREATED,
            submission_response.data,
        )
        self.assertEqual(
            submission_response.data["acknowledgement_email_status"],
            AcknowledgementEmailStatus.SENT,
        )
        self.assertNotIn("email", submission_response.data)
        self.assertNotIn("phone_number", submission_response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["acceptance-donor@example.com"])
        submission = DonationSubmission.objects.get(
            pk=submission_response.data["id"]
        )

        manager_list = manager_client.get(
            "/api/v1/donations/management/submissions/",
            {"search": submission.email},
        )
        manager_detail = manager_client.get(
            (
                "/api/v1/donations/management/submissions/"
                f"{submission.id}/"
            )
        )
        self.assertEqual(manager_list.status_code, status.HTTP_200_OK)
        self.assertEqual(manager_list.data["count"], 1)
        self.assertEqual(manager_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(
            manager_detail.data["details"],
            "Books and workshop equipment.",
        )

        footer_update = manager_client.patch(
            "/api/v1/content/site/",
            {
                "contact_email": "contact@askforsuccess.example",
                "instagram_url": "https://www.instagram.com/askforsuccess",
            },
            format="json",
        )
        self.assertEqual(
            footer_update.status_code,
            status.HTTP_200_OK,
            footer_update.data,
        )
        public_footer = public_client.get("/api/v1/content/site/")
        self.assertEqual(public_footer.status_code, status.HTTP_200_OK)
        self.assertEqual(
            public_footer.data["contact_email"],
            "contact@askforsuccess.example",
        )
        self.assertEqual(
            public_footer.data["instagram_url"],
            "https://www.instagram.com/askforsuccess",
        )

        manager_timeline = self.actor_timeline(self.hr_manager)
        self.assertTrue(
            any(
                record["domain"] == AuditDomain.CONTENT
                and record["action"] == AuditAction.API_UPDATED
                for record in manager_timeline
            )
        )
