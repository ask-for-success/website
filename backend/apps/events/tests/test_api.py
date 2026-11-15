from datetime import timedelta

from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.memberships.models import Membership, MembershipStatus

from ..models import (
    Event,
    EventQuestion,
    EventQuestionOption,
    EventQuestionType,
    EventRegistration,
    EventScanner,
    EventTicket,
    PublicationStatus,
    QrDeliveryStatus,
)
from ..operations import create_event_registration


class EventTestDataMixin:
    @classmethod
    def create_common_data(cls):
        cls.content_manager = User.objects.create_user(
            email="content-manager@example.com",
            first_name="Content",
            last_name="Manager",
            phone_number="+212600000501",
            password="StrongPassword!2026",
        )
        cls.content_manager.groups.add(Group.objects.get(name="content_manager"))
        cls.ordinary_user = User.objects.create_user(
            email="ordinary-user@example.com",
            first_name="Ordinary",
            last_name="User",
            phone_number="+212600000502",
            password="StrongPassword!2026",
        )
        cls.member_user = User.objects.create_user(
            email="event-scanner@example.com",
            first_name="Event",
            last_name="Scanner",
            phone_number="+212600000503",
            password="StrongPassword!2026",
        )
        cls.membership = Membership()
        cls.membership.user = cls.member_user
        cls.membership.status = MembershipStatus.ACTIVE
        cls.membership.save()

    def event_payload(self, **overrides):
        starts_at = timezone.now() + timedelta(days=2)
        payload = {
            "title": "Success Forum",
            "summary": "Public meeting",
            "description": "Event description",
            "location": "Casablanca",
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=3)).isoformat(),
            "publication_status": PublicationStatus.PUBLISHED,
            "requires_qr_code": True,
            "questions": [
                {
                    "label": "Your name",
                    "question_type": EventQuestionType.SHORT_TEXT,
                    "is_required": True,
                    "display_order": 1,
                    "options": [],
                },
                {
                    "label": "Your background",
                    "question_type": EventQuestionType.SINGLE_CHOICE,
                    "is_required": True,
                    "display_order": 2,
                    "options": [
                        {"label": "Student", "display_order": 1},
                        {"label": "Professional", "display_order": 2},
                    ],
                },
                {
                    "label": "Do you accept the terms?",
                    "question_type": EventQuestionType.YES_NO,
                    "is_required": True,
                    "display_order": 3,
                    "options": [],
                },
                {
                    "label": "Your preferred subjects",
                    "question_type": EventQuestionType.MULTIPLE_CHOICE,
                    "is_required": True,
                    "display_order": 4,
                    "options": [
                        {"label": "Entrepreneurship", "display_order": 1},
                        {"label": "Technology", "display_order": 2},
                        {"label": "Communication", "display_order": 3},
                    ],
                },
            ],
        }
        payload.update(overrides)
        return payload

    def create_event_through_api(self, **overrides):
        self.client.force_authenticate(self.content_manager)
        return self.client.post(
            "/api/v1/events/",
            self.event_payload(**overrides),
            format="json",
        )

    @staticmethod
    def registration_payload(event):
        questions = list(event.questions.prefetch_related("options"))
        name_question = questions[0]
        background_question = questions[1]
        terms_question = questions[2]
        subjects_question = questions[3]
        background_option = background_question.options.first()
        subject_options = list(
            subjects_question.options.values_list("id", flat=True)
        )
        return {
            "email": "visitor@example.com",
            "answers": [
                {"question_id": str(name_question.id), "value": "Visitor"},
                {
                    "question_id": str(background_question.id),
                    "value": str(background_option.id),
                },
                {"question_id": str(terms_question.id), "value": True},
                {
                    "question_id": str(subjects_question.id),
                    "value": [str(value) for value in subject_options[:2]],
                },
            ],
        }


class EventApiTests(EventTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_common_data()

    def test_content_manager_creates_event_and_form(self):
        response = self.create_event_through_api()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = Event.objects.get()
        self.assertEqual(event.created_by, self.content_manager)
        self.assertEqual(event.questions.count(), 4)
        question = event.questions.get(
            question_type=EventQuestionType.SINGLE_CHOICE
        )
        self.assertEqual(question.options.count(), 2)

    def test_ordinary_user_cannot_create_event(self):
        self.client.force_authenticate(self.ordinary_user)

        response = self.client.post(
            "/api/v1/events/",
            self.event_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_registration_sends_qr_code_without_account(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        user_count = User.objects.count()
        self.client.force_authenticate(user=None)

        response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), user_count)
        registration = EventRegistration.objects.get()
        self.assertEqual(registration.email, "visitor@example.com")
        self.assertEqual(registration.answers.count(), 4)
        self.assertEqual(registration.ticket.delivery_status, QrDeliveryStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["visitor@example.com"])
        self.assertEqual(mail.outbox[0].attachments[0][2], "image/png")

    def test_same_email_cannot_register_twice(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        payload = self.registration_payload(event)
        self.client.force_authenticate(user=None)
        first_response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            payload,
            format="json",
        )
        payload["email"] = "VISITOR@example.com"

        second_response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            payload,
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EventRegistration.objects.count(), 1)

    def test_event_without_qr_code_does_not_create_ticket(self):
        creation = self.create_event_through_api(requires_qr_code=False)
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)

        response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(EventTicket.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_required_questions_are_validated(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)

        response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            {"email": "incomplete@example.com", "answers": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("answers", response.data)

    def test_content_manager_assigns_active_member_as_scanner(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])

        response = self.client.post(
            f"/api/v1/events/{event.id}/scanners/",
            {"membership_id": str(self.membership.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        scanner = EventScanner.objects.get()
        self.assertEqual(scanner.membership, self.membership)
        self.assertEqual(scanner.assigned_by, self.content_manager)

    def test_check_in_is_unique_and_reports_second_scan(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        result = create_event_registration(
            event=event,
            email="check-in@example.com",
            answers=self.registration_payload(event)["answers"],
        )
        EventScanner.objects.create(
            event=event,
            membership=self.membership,
            assigned_by=self.content_manager,
        )
        self.client.force_authenticate(self.member_user)

        first_response = self.client.post(
            f"/api/v1/events/{event.id}/check-ins/",
            {"qr_code": result.qr_code},
            format="json",
        )
        second_response = self.client.post(
            f"/api/v1/events/{event.id}/check-ins/",
            {"qr_code": result.qr_code},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data["status"], "checked_in")
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data["status"], "already_checked_in")

    def test_unassigned_member_cannot_check_in_ticket(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        result = create_event_registration(
            event=event,
            email="unassigned@example.com",
            answers=self.registration_payload(event)["answers"],
        )
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            f"/api/v1/events/{event.id}/check-ins/",
            {"qr_code": result.qr_code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_form_cannot_be_replaced_after_registration(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        create_event_registration(
            event=event,
            email="registered@example.com",
            answers=self.registration_payload(event)["answers"],
        )
        self.client.force_authenticate(self.content_manager)

        response = self.client.patch(
            f"/api/v1/events/{event.id}/",
            {"questions": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_schema_documents_event_routes(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/schema/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/api/v1/events/", response.data["paths"])
        self.assertIn(
            "/api/v1/events/{event_id}/registrations/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/events/{event_id}/check-ins/",
            response.data["paths"],
        )


class EventModelTests(EventTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.create_common_data()

    def test_multiple_choice_question_accepts_multiple_options(self):
        starts_at = timezone.now() + timedelta(days=2)
        event = Event.objects.create(
            title="Workshop",
            description="Description",
            location="Rabat",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=2),
            publication_status=PublicationStatus.PUBLISHED,
            created_by=self.content_manager,
        )
        question = EventQuestion.objects.create(
            event=event,
            label="Select your subjects",
            question_type=EventQuestionType.MULTIPLE_CHOICE,
            display_order=1,
        )
        EventQuestionOption.objects.create(
            question=question,
            label="Entrepreneurship",
            display_order=1,
        )
        EventQuestionOption.objects.create(
            question=question,
            label="Technology",
            display_order=2,
        )

        self.assertEqual(question.options.count(), 2)
