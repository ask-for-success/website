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
    EmailDeliveryStatus,
    Event,
    EventNotificationType,
    EventParticipantNotification,
    EventQuestion,
    EventQuestionOption,
    EventQuestionType,
    EventRegistration,
    EventRegistrationSource,
    EventRegistrationStatus,
    EventScanner,
    EventTicket,
    PublicationStatus,
    QrDeliveryStatus,
    RegistrationCancellationSource,
)
from ..operations import build_cancellation_token, create_event_registration


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
        self.assertEqual(
            registration.confirmation_email_status,
            EmailDeliveryStatus.SENT,
        )
        self.assertEqual(registration.ticket.delivery_status, QrDeliveryStatus.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["visitor@example.com"])
        self.assertEqual(mail.outbox[0].attachments[0][2], "image/png")
        self.assertIn("/events/registrations/cancel?token=", mail.outbox[0].body)

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

    def test_event_without_qr_code_sends_cancellation_link_without_ticket(self):
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
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments, [])
        self.assertIn("/events/registrations/cancel?token=", mail.outbox[0].body)

    def test_capacity_closes_registration_automatically(self):
        creation = self.create_event_through_api(capacity=1)
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)

        first = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        second_payload = self.registration_payload(event)
        second_payload["email"] = "second@example.com"
        second = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            second_payload,
            format="json",
        )
        detail = self.client.get(f"/api/v1/events/{event.id}/")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(detail.data["active_registration_count"], 1)
        self.assertEqual(detail.data["seats_remaining"], 0)
        self.assertTrue(detail.data["is_registration_full"])
        self.assertFalse(detail.data["is_registration_open"])

    def test_self_cancellation_releases_capacity_and_allows_another_person(self):
        creation = self.create_event_through_api(capacity=1)
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)
        first = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        registration = EventRegistration.objects.get(pk=first.data["id"])

        cancellation = self.client.post(
            "/api/v1/events/registrations/cancel/",
            {
                "cancellation_token": build_cancellation_token(
                    registration.id
                )
            },
            format="json",
        )
        replacement_payload = self.registration_payload(event)
        replacement_payload["email"] = "replacement@example.com"
        replacement = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            replacement_payload,
            format="json",
        )

        self.assertEqual(cancellation.status_code, status.HTTP_200_OK)
        self.assertEqual(replacement.status_code, status.HTTP_201_CREATED)
        registration.refresh_from_db()
        self.assertEqual(
            registration.status,
            EventRegistrationStatus.CANCELLED,
        )
        self.assertEqual(
            registration.cancellation_source,
            RegistrationCancellationSource.SELF_SERVICE,
        )
        self.assertEqual(event.active_registration_count(), 1)

    def test_self_cancellation_is_blocked_during_final_24_hours(self):
        starts_at = timezone.now() + timedelta(hours=20)
        creation = self.create_event_through_api(
            starts_at=starts_at.isoformat(),
            ends_at=(starts_at + timedelta(hours=2)).isoformat(),
        )
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)
        registration_response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        registration = EventRegistration.objects.get(
            pk=registration_response.data["id"]
        )

        response = self.client.post(
            "/api/v1/events/registrations/cancel/",
            {"cancellation_token": build_cancellation_token(registration.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        registration.refresh_from_db()
        self.assertEqual(
            registration.status,
            EventRegistrationStatus.REGISTERED,
        )

    def test_content_manager_adds_manual_participant_and_email_is_sent(self):
        creation = self.create_event_through_api(capacity=2)
        event = Event.objects.get(pk=creation.data["id"])
        payload = self.registration_payload(event)
        payload["email"] = "manual-participant@example.com"

        response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/manual/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        registration = EventRegistration.objects.get(pk=response.data["id"])
        self.assertEqual(registration.source, EventRegistrationSource.MANUAL)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            ["manual-participant@example.com"],
        )

    def test_manual_participant_cannot_exceed_capacity(self):
        creation = self.create_event_through_api(capacity=1)
        event = Event.objects.get(pk=creation.data["id"])
        first_payload = self.registration_payload(event)
        first_payload["email"] = "first-manual@example.com"
        first = self.client.post(
            f"/api/v1/events/{event.id}/registrations/manual/",
            first_payload,
            format="json",
        )
        second_payload = self.registration_payload(event)
        second_payload["email"] = "second-manual@example.com"

        second = self.client.post(
            f"/api/v1/events/{event.id}/registrations/manual/",
            second_payload,
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(event.active_registration_count(), 1)

    def test_reschedule_notifies_participant_and_attaches_same_qr_code(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)
        registration_response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        original_attachment = mail.outbox[0].attachments[0][1]
        ticket_hash = EventTicket.objects.get().qr_code_hash
        new_start = event.starts_at + timedelta(days=5)
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            f"/api/v1/events/{event.id}/reschedule/",
            {
                "starts_at": new_start.isoformat(),
                "ends_at": (new_start + timedelta(hours=3)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notification_count"], 1)
        self.assertEqual(response.data["sent_count"], 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].attachments[0][1], original_attachment)
        self.assertIn("has been rescheduled", mail.outbox[1].body)
        self.assertEqual(EventTicket.objects.get().qr_code_hash, ticket_hash)
        self.assertEqual(
            EventParticipantNotification.objects.get().notification_type,
            EventNotificationType.RESCHEDULED,
        )

    def test_direct_schedule_update_is_blocked_after_registration(self):
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
            {"starts_at": (event.starts_at + timedelta(days=1)).isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permanent_cancellation_invalidates_registrations_and_notifies(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)
        registration_response = self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        mail.outbox.clear()
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            f"/api/v1/events/{event.id}/cancel/",
            {},
            format="json",
        )

        self.assertEqual(registration_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        registration = EventRegistration.objects.get()
        self.assertEqual(event.publication_status, PublicationStatus.CANCELLED)
        self.assertEqual(
            registration.status,
            EventRegistrationStatus.CANCELLED,
        )
        self.assertEqual(
            registration.cancellation_source,
            RegistrationCancellationSource.EVENT_CANCELLED,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("will no longer take place", mail.outbox[0].body)
        notification = EventParticipantNotification.objects.get()
        self.assertEqual(
            notification.notification_type,
            EventNotificationType.CANCELLED,
        )
        self.assertEqual(
            notification.delivery_status,
            EmailDeliveryStatus.SENT,
        )

    def test_lifecycle_notification_can_be_deliberately_disabled(self):
        creation = self.create_event_through_api()
        event = Event.objects.get(pk=creation.data["id"])
        self.client.force_authenticate(user=None)
        self.client.post(
            f"/api/v1/events/{event.id}/registrations/",
            self.registration_payload(event),
            format="json",
        )
        mail.outbox.clear()
        self.client.force_authenticate(self.content_manager)

        response = self.client.post(
            f"/api/v1/events/{event.id}/cancel/",
            {"notify_participants": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["notification_count"], 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EventParticipantNotification.objects.exists())

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

    def test_scanner_assignment_for_one_event_does_not_grant_other_events(self):
        first_creation = self.create_event_through_api(title="First Event")
        first_event = Event.objects.get(pk=first_creation.data["id"])
        second_creation = self.create_event_through_api(title="Second Event")
        second_event = Event.objects.get(pk=second_creation.data["id"])
        second_event_registration = create_event_registration(
            event=second_event,
            email="second-event@example.com",
            answers=self.registration_payload(second_event)["answers"],
        )
        EventScanner.objects.create(
            event=first_event,
            membership=self.membership,
            assigned_by=self.content_manager,
        )
        self.client.force_authenticate(self.member_user)

        response = self.client.post(
            f"/api/v1/events/{second_event.id}/check-ins/",
            {"qr_code": second_event_registration.qr_code},
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
        self.assertIn(
            "/api/v1/events/{event_id}/reschedule/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/events/{event_id}/cancel/",
            response.data["paths"],
        )
        self.assertIn(
            "/api/v1/events/registrations/cancel/",
            response.data["paths"],
        )

    def test_public_event_list_filters_upcoming_and_past(self):
        upcoming_creation = self.create_event_through_api()
        past_start = timezone.now() - timedelta(days=3)
        past = Event.objects.create(
            title="Past workshop",
            summary="Completed event",
            description="A completed workshop.",
            location="Rabat",
            starts_at=past_start,
            ends_at=past_start + timedelta(hours=2),
            publication_status=PublicationStatus.PUBLISHED,
            created_by=self.content_manager,
        )
        self.client.force_authenticate(user=None)

        upcoming_response = self.client.get(
            "/api/v1/events/",
            {"timing": "upcoming"},
        )
        past_response = self.client.get(
            "/api/v1/events/",
            {"timing": "past"},
        )

        self.assertEqual(upcoming_response.status_code, status.HTTP_200_OK)
        self.assertEqual(past_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in upcoming_response.data},
            {upcoming_creation.data["id"]},
        )
        self.assertEqual(
            {item["id"] for item in past_response.data},
            {str(past.id)},
        )

    def test_invalid_event_timing_filter_is_rejected(self):
        response = self.client.get("/api/v1/events/", {"timing": "later"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
