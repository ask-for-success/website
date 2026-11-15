import hashlib
import uuid
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import quote

import qrcode
from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.memberships.models import Membership, MembershipStatus

from .models import (
    Event,
    EventAnswer,
    EventCheckIn,
    EmailDeliveryStatus,
    EventNotificationType,
    EventParticipantNotification,
    EventQuestionType,
    EventRegistration,
    EventRegistrationSource,
    EventRegistrationStatus,
    PublicationStatus,
    RegistrationCancellationSource,
    EventScanner,
    EventTicket,
    QrDeliveryStatus,
)


@dataclass(frozen=True)
class EventRegistrationResult:
    registration: EventRegistration
    ticket: EventTicket | None
    qr_code: str | None


@dataclass(frozen=True)
class EventCheckInResult:
    status: str
    check_in: EventCheckIn


@dataclass(frozen=True)
class EventLifecycleResult:
    event: Event
    notification_type: str
    notification_count: int
    sent_count: int
    failed_count: int


def ensure_content_manager(user) -> None:
    if user.is_superuser:
        return
    if not user.groups.filter(name="content_manager").exists():
        raise PermissionDenied(
            "This operation is restricted to content managers."
        )


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _qr_signer() -> signing.Signer:
    return signing.Signer(salt="events.qr.v1")


def _cancellation_signer() -> signing.Signer:
    return signing.Signer(salt="events.registration-cancellation.v1")


def build_qr_code(ticket_id) -> str:
    return _qr_signer().sign(str(ticket_id))


def rebuild_qr_code(ticket: EventTicket) -> str | None:
    qr_code = build_qr_code(ticket.id)
    if _hash_value(qr_code) != ticket.qr_code_hash:
        return None
    return qr_code


def build_cancellation_token(registration_id) -> str:
    return _cancellation_signer().sign(str(registration_id))


def build_cancellation_link(registration: EventRegistration) -> str:
    token = quote(build_cancellation_token(registration.id), safe="")
    base_url = settings.PUBLIC_WEB_URL.rstrip("/")
    return f"{base_url}/events/registrations/cancel?token={token}"


def _format_event_time(value) -> str:
    return timezone.localtime(value).strftime("%A, %d %B %Y at %H:%M %Z")


def _registration_window_is_open(event: Event) -> bool:
    now = timezone.now()
    if event.publication_status != PublicationStatus.PUBLISHED:
        return False
    if event.registration_opens_at and now < event.registration_opens_at:
        return False
    closes_at = event.registration_closes_at or event.starts_at
    return now < closes_at


def _is_empty(value) -> bool:
    return value is None or value == "" or value == []


def _validate_answer(question, value):
    question_type = question.question_type
    if question_type in {
        EventQuestionType.SHORT_TEXT,
        EventQuestionType.LONG_TEXT,
        EventQuestionType.EMAIL,
        EventQuestionType.PHONE,
    }:
        if not isinstance(value, str):
            raise ValidationError("The answer must be text.")
        value = value.strip()
        if question_type == EventQuestionType.EMAIL:
            validate_email(value)
        return value

    if question_type == EventQuestionType.YES_NO:
        if not isinstance(value, bool):
            raise ValidationError("The answer must be true or false.")
        return value

    option_ids = {
        str(option_id)
        for option_id in question.options.values_list("id", flat=True)
    }
    if question_type == EventQuestionType.SINGLE_CHOICE:
        value = str(value)
        if value not in option_ids:
            raise ValidationError("The selected option is invalid.")
        return value

    if question_type == EventQuestionType.MULTIPLE_CHOICE:
        if not isinstance(value, list):
            raise ValidationError("The answer must be a list of options.")
        values = [str(item) for item in value]
        if len(values) != len(set(values)):
            raise ValidationError("An option cannot be selected more than once.")
        if not set(values).issubset(option_ids):
            raise ValidationError("A selected option is invalid.")
        return values

    raise ValidationError("This question type is not supported.")


def _prepare_answers(event: Event, answers: list[dict]):
    questions = {
        str(question.id): question
        for question in event.questions.prefetch_related("options")
    }
    answers_by_question = {}
    errors = {}

    for position, answer in enumerate(answers):
        question_id = str(answer["question_id"])
        if question_id in answers_by_question:
            errors[str(position)] = "This question has more than one answer."
            continue
        question = questions.get(question_id)
        if question is None:
            errors[str(position)] = "This question does not belong to the event."
            continue
        value = answer.get("value")
        if _is_empty(value):
            if question.is_required:
                errors[str(position)] = "This question is required."
            continue
        try:
            answers_by_question[question_id] = _validate_answer(question, value)
        except ValidationError as error:
            errors[str(position)] = list(error.messages)

    for question_id, question in questions.items():
        if question.is_required and question_id not in answers_by_question:
            errors[str(question.id)] = "This question is required."

    if errors:
        messages = [
            f"{identifier}: {message}"
            for identifier, message in errors.items()
        ]
        raise ValidationError({"answers": messages})
    return [
        (questions[question_id], value)
        for question_id, value in answers_by_question.items()
    ]


def create_event_registration(
    *,
    event: Event,
    email: str,
    answers: list[dict],
    source: str = EventRegistrationSource.PUBLIC,
) -> EventRegistrationResult:
    email = email.strip().lower()
    validate_email(email)
    qr_code = None
    ticket = None

    try:
        with transaction.atomic():
            locked_event = Event.objects.select_for_update().get(pk=event.pk)
            if not _registration_window_is_open(locked_event):
                raise ValidationError(
                    {"event": "Registration is not open for this event."}
                )
            if locked_event.is_registration_full():
                raise ValidationError(
                    {"event": "The event has reached its capacity."}
                )
            prepared_answers = _prepare_answers(locked_event, answers)
            registration = EventRegistration(
                event=locked_event,
                email=email,
                source=source,
            )
            registration.full_clean()
            registration.save()
            for question, value in prepared_answers:
                answer = EventAnswer(
                    registration=registration,
                    question=question,
                    value=value,
                )
                answer.full_clean()
                answer.save()

            if locked_event.requires_qr_code:
                ticket_id = uuid.uuid4()
                qr_code = build_qr_code(ticket_id)
                ticket = EventTicket.objects.create(
                    id=ticket_id,
                    registration=registration,
                    qr_code_hash=_hash_value(qr_code),
                )
    except IntegrityError as error:
        raise ValidationError(
            {"email": "This email is already registered for this event."}
        ) from error

    return EventRegistrationResult(
        registration=registration,
        ticket=ticket,
        qr_code=qr_code,
    )


def send_registration_confirmation_email(
    result: EventRegistrationResult,
) -> None:
    registration = result.registration
    ticket = result.ticket
    event = result.registration.event
    cancellation_link = build_cancellation_link(registration)
    cancellation_deadline = _format_event_time(
        registration.cancellation_deadline
    )
    try:
        message = EmailMessage(
            subject=f"Your registration for {event.title}",
            body=(
                f"Your registration for {event.title} is confirmed.\n\n"
                f"The event starts {_format_event_time(event.starts_at)}.\n\n"
                "You can cancel until "
                f"{cancellation_deadline} using this secure link:\n"
                f"{cancellation_link}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.email],
        )
        if ticket is not None and result.qr_code is not None:
            image = qrcode.make(result.qr_code)
            content = BytesIO()
            image.save(content, format="PNG")
            message.body += (
                "\n\nPresent the attached QR code when you arrive."
            )
            message.attach("qr-code.png", content.getvalue(), "image/png")
        sent_count = message.send(fail_silently=False)
        if sent_count != 1:
            raise RuntimeError("The email service did not confirm delivery.")
    except Exception as error:
        registration.confirmation_email_status = EmailDeliveryStatus.FAILED
        registration.confirmation_email_error = str(error)[:2000]
        registration.save(
            update_fields=(
                "confirmation_email_status",
                "confirmation_email_error",
                "updated_at",
            )
        )
        if ticket is not None:
            ticket.delivery_status = QrDeliveryStatus.FAILED
            ticket.delivery_error = str(error)[:2000]
            ticket.save(
                update_fields=(
                    "delivery_status",
                    "delivery_error",
                    "updated_at",
                )
            )
        return

    sent_at = timezone.now()
    registration.confirmation_email_status = EmailDeliveryStatus.SENT
    registration.confirmation_email_sent_at = sent_at
    registration.confirmation_email_error = ""
    registration.save(
        update_fields=(
            "confirmation_email_status",
            "confirmation_email_sent_at",
            "confirmation_email_error",
            "updated_at",
        )
    )
    if ticket is not None:
        ticket.delivery_status = QrDeliveryStatus.SENT
        ticket.sent_at = sent_at
        ticket.delivery_error = ""
        ticket.save(
            update_fields=(
                "delivery_status",
                "sent_at",
                "delivery_error",
                "updated_at",
            )
        )


@transaction.atomic
def cancel_event_registration(*, cancellation_token: str) -> EventRegistration:
    try:
        registration_id = uuid.UUID(
            _cancellation_signer().unsign(cancellation_token)
        )
    except (signing.BadSignature, ValueError) as error:
        raise ValidationError(
            {"cancellation_token": "This cancellation link is invalid."}
        ) from error

    try:
        registration = (
            EventRegistration.objects.select_for_update()
            .select_related("event")
            .get(pk=registration_id)
        )
    except EventRegistration.DoesNotExist as error:
        raise ValidationError(
            {"cancellation_token": "This cancellation link is invalid."}
        ) from error

    if registration.status == EventRegistrationStatus.CANCELLED:
        raise ValidationError(
            {"registration": "This registration is already cancelled."}
        )
    if timezone.now() >= registration.cancellation_deadline:
        raise ValidationError(
            {
                "registration": (
                    "Cancellation closes 24 hours before the event starts."
                )
            }
        )

    registration.status = EventRegistrationStatus.CANCELLED
    registration.cancelled_at = timezone.now()
    registration.cancellation_source = (
        RegistrationCancellationSource.SELF_SERVICE
    )
    registration.save(
        update_fields=(
            "status",
            "cancelled_at",
            "cancellation_source",
            "updated_at",
        )
    )
    return registration


@transaction.atomic
def reschedule_event(
    *,
    event: Event,
    starts_at,
    ends_at,
    updated_by,
) -> tuple[Event, list[EventRegistration]]:
    ensure_content_manager(updated_by)
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.publication_status == PublicationStatus.CANCELLED:
        raise ValidationError(
            {"event": "A permanently cancelled event cannot be rescheduled."}
        )
    if starts_at <= timezone.now():
        raise ValidationError({"starts_at": "The new start time must be future."})

    schedule_delta = starts_at - locked_event.starts_at
    locked_event.starts_at = starts_at
    locked_event.ends_at = ends_at
    if locked_event.registration_closes_at:
        locked_event.registration_closes_at += schedule_delta
    locked_event.full_clean()
    locked_event.save(
        update_fields=(
            "starts_at",
            "ends_at",
            "registration_closes_at",
            "updated_at",
        )
    )
    registrations = list(
        locked_event.registrations.filter(
            status=EventRegistrationStatus.REGISTERED
        ).select_related("ticket")
    )
    return locked_event, registrations


@transaction.atomic
def permanently_cancel_event(
    *,
    event: Event,
    cancelled_by,
) -> tuple[Event, list[EventRegistration]]:
    ensure_content_manager(cancelled_by)
    locked_event = Event.objects.select_for_update().get(pk=event.pk)
    if locked_event.publication_status == PublicationStatus.CANCELLED:
        raise ValidationError({"event": "This event is already cancelled."})

    registrations = list(
        locked_event.registrations.filter(
            status=EventRegistrationStatus.REGISTERED
        ).select_related("ticket")
    )
    now = timezone.now()
    locked_event.publication_status = PublicationStatus.CANCELLED
    locked_event.cancelled_at = now
    locked_event.cancelled_by = cancelled_by
    locked_event.save(
        update_fields=(
            "publication_status",
            "cancelled_at",
            "cancelled_by",
            "updated_at",
        )
    )
    EventRegistration.objects.filter(
        id__in=[registration.id for registration in registrations]
    ).update(
        status=EventRegistrationStatus.CANCELLED,
        cancelled_at=now,
        cancellation_source=RegistrationCancellationSource.EVENT_CANCELLED,
        updated_at=now,
    )
    return locked_event, registrations


def send_event_participant_notifications(
    *,
    event: Event,
    registrations: list[EventRegistration],
    notification_type: str,
) -> EventLifecycleResult:
    sent_count = 0
    failed_count = 0
    for registration in registrations:
        notification = EventParticipantNotification.objects.create(
            event=event,
            registration=registration,
            notification_type=notification_type,
        )
        try:
            if notification_type == EventNotificationType.RESCHEDULED:
                subject = f"New date for {event.title}"
                body = (
                    f"{event.title} has been rescheduled.\n\n"
                    f"The new start time is {_format_event_time(event.starts_at)}.\n"
                    f"The new end time is {_format_event_time(event.ends_at)}.\n\n"
                    "Your registration and original QR code remain valid.\n\n"
                    "You can cancel until "
                    f"{_format_event_time(registration.cancellation_deadline)} "
                    "using this secure link:\n"
                    f"{build_cancellation_link(registration)}"
                )
            else:
                subject = f"{event.title} has been cancelled"
                body = (
                    f"We are sorry, but {event.title} will no longer take place.\n\n"
                    "Your registration and QR code are now cancelled."
                )

            message = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[registration.email],
            )
            if (
                notification_type == EventNotificationType.RESCHEDULED
                and event.requires_qr_code
            ):
                try:
                    ticket = registration.ticket
                except EventTicket.DoesNotExist:
                    ticket = None
                qr_code = rebuild_qr_code(ticket) if ticket else None
                if qr_code:
                    image = qrcode.make(qr_code)
                    content = BytesIO()
                    image.save(content, format="PNG")
                    message.attach(
                        "qr-code.png",
                        content.getvalue(),
                        "image/png",
                    )
            delivered = message.send(fail_silently=False)
            if delivered != 1:
                raise RuntimeError(
                    "The email service did not confirm delivery."
                )
        except Exception as error:
            failed_count += 1
            notification.delivery_status = EmailDeliveryStatus.FAILED
            notification.delivery_error = str(error)[:2000]
            notification.save(
                update_fields=(
                    "delivery_status",
                    "delivery_error",
                    "updated_at",
                )
            )
            continue

        sent_count += 1
        notification.delivery_status = EmailDeliveryStatus.SENT
        notification.sent_at = timezone.now()
        notification.delivery_error = ""
        notification.save(
            update_fields=(
                "delivery_status",
                "sent_at",
                "delivery_error",
                "updated_at",
            )
        )

    return EventLifecycleResult(
        event=event,
        notification_type=notification_type,
        notification_count=len(registrations),
        sent_count=sent_count,
        failed_count=failed_count,
    )


@transaction.atomic
def assign_event_scanner(
    *,
    event: Event,
    membership: Membership,
    assigned_by,
) -> EventScanner:
    ensure_content_manager(assigned_by)
    if (
        membership.status != MembershipStatus.ACTIVE
        or not membership.user.is_active
    ):
        raise ValidationError(
            {"membership_id": "The scanner must be an active member."}
        )

    scanner, created = EventScanner.objects.get_or_create(
        event=event,
        membership=membership,
        defaults={"assigned_by": assigned_by},
    )
    if not created:
        scanner.assigned_by = assigned_by
        scanner.is_active = True
    scanner.full_clean()
    scanner.save()
    return scanner


def remove_event_scanner(*, scanner: EventScanner, removed_by) -> None:
    ensure_content_manager(removed_by)
    scanner.is_active = False
    scanner.save(update_fields=("is_active", "updated_at"))


def ensure_event_scanner(*, event: Event, user) -> None:
    if user.is_superuser:
        return
    assignments = EventScanner.objects.filter(
        event=event,
        is_active=True,
    )
    is_authorized = any(
        assignment.membership.user_id == user.id
        and assignment.membership.status == MembershipStatus.ACTIVE
        for assignment in assignments
    )
    if not is_authorized:
        raise PermissionDenied(
            "You are not an active scanner for this event."
        )


@transaction.atomic
def check_in_event_registration(
    *,
    event: Event,
    qr_code: str,
    user,
) -> EventCheckInResult:
    ensure_event_scanner(event=event, user=user)
    if event.publication_status == PublicationStatus.CANCELLED:
        raise ValidationError(
            {"event": "Check-in is unavailable for a cancelled event."}
        )
    try:
        ticket = (
            EventTicket.objects.select_for_update()
            .select_related("registration")
            .get(
                qr_code_hash=_hash_value(qr_code),
                registration__event=event,
                registration__status=EventRegistrationStatus.REGISTERED,
            )
        )
    except EventTicket.DoesNotExist as error:
        raise ValidationError(
            {"qr_code": "This QR code is invalid for this event."}
        ) from error

    check_in, created = EventCheckIn.objects.get_or_create(
        ticket=ticket,
        defaults={"checked_in_by": user},
    )
    return EventCheckInResult(
        status="checked_in" if created else "already_checked_in",
        check_in=check_in,
    )
