import hashlib
import secrets
from dataclasses import dataclass
from io import BytesIO

import qrcode
from django.conf import settings
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
    EventQuestionType,
    EventRegistration,
    EventRegistrationStatus,
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


def ensure_content_manager(user) -> None:
    if user.is_superuser:
        return
    if not user.groups.filter(name="content_manager").exists():
        raise PermissionDenied(
            "This operation is restricted to content managers."
        )


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
) -> EventRegistrationResult:
    if not event.accepts_registrations():
        raise ValidationError(
            {"event": "Registration is not open for this event."}
        )

    email = email.strip().lower()
    validate_email(email)
    prepared_answers = _prepare_answers(event, answers)
    qr_code = None
    ticket = None

    try:
        with transaction.atomic():
            registration = EventRegistration(event=event, email=email)
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

            if event.requires_qr_code:
                qr_code = secrets.token_urlsafe(32)
                ticket = EventTicket.objects.create(
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


def send_qr_code_email(result: EventRegistrationResult) -> None:
    if result.ticket is None or result.qr_code is None:
        return

    ticket = result.ticket
    event = result.registration.event
    try:
        image = qrcode.make(result.qr_code)
        content = BytesIO()
        image.save(content, format="PNG")
        message = EmailMessage(
            subject=f"Your registration for {event.title}",
            body=(
                f"Your registration for {event.title} is confirmed.\n\n"
                "Present the attached QR code when you arrive."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[result.registration.email],
        )
        message.attach("qr-code.png", content.getvalue(), "image/png")
        sent_count = message.send(fail_silently=False)
        if sent_count != 1:
            raise RuntimeError("The email service did not confirm delivery.")
    except Exception as error:
        ticket.delivery_status = QrDeliveryStatus.FAILED
        ticket.delivery_error = str(error)[:2000]
        ticket.save(
            update_fields=("delivery_status", "delivery_error", "updated_at")
        )
        return

    ticket.delivery_status = QrDeliveryStatus.SENT
    ticket.sent_at = timezone.now()
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
