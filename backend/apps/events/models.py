import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.memberships.models import Membership, MembershipStatus


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class EventQuestionType(models.TextChoices):
    SHORT_TEXT = "short_text", "Short text"
    LONG_TEXT = "long_text", "Long text"
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"
    SINGLE_CHOICE = "single_choice", "Single choice"
    MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
    YES_NO = "yes_no", "Yes or no"


class EventRegistrationStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    CANCELLED = "cancelled", "Cancelled"


class QrDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    requires_qr_code = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events"
        ordering = ("starts_at", "title")

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.location = self.location.strip()
        if self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "The end time must be after the start time."}
            )
        if (
            self.registration_opens_at
            and self.registration_closes_at
            and self.registration_closes_at <= self.registration_opens_at
        ):
            raise ValidationError(
                {
                    "registration_closes_at": (
                        "Registration must close after it opens."
                    )
                }
            )
        if (
            self.registration_closes_at
            and self.registration_closes_at > self.starts_at
        ):
            raise ValidationError(
                {
                    "registration_closes_at": (
                        "Registration must close before the event starts."
                    )
                }
            )

    def accepts_registrations(self) -> bool:
        now = timezone.now()
        if self.publication_status != PublicationStatus.PUBLISHED:
            return False
        if self.registration_opens_at and now < self.registration_opens_at:
            return False
        closes_at = self.registration_closes_at or self.starts_at
        return now < closes_at

    def __str__(self) -> str:
        return self.title


class EventQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    label = models.CharField(max_length=300)
    question_type = models.CharField(
        max_length=32,
        choices=EventQuestionType.choices,
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_questions"
        ordering = ("display_order", "created_at")
        constraints = (
            models.UniqueConstraint(
                fields=("event", "display_order"),
                name="event_questions_order_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.label = self.label.strip()

    def __str__(self) -> str:
        return self.label


class EventQuestionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        EventQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "event_question_options"
        ordering = ("display_order", "id")
        constraints = (
            models.UniqueConstraint(
                fields=("question", "display_order"),
                name="event_question_options_order_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.label = self.label.strip()
        if self.question_id and self.question.question_type not in {
            EventQuestionType.SINGLE_CHOICE,
            EventQuestionType.MULTIPLE_CHOICE,
        }:
            raise ValidationError(
                {"question": "Only choice questions can contain options."}
            )

    def __str__(self) -> str:
        return self.label


class EventRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    email = models.EmailField(max_length=254)
    status = models.CharField(
        max_length=16,
        choices=EventRegistrationStatus.choices,
        default=EventRegistrationStatus.REGISTERED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_registrations"
        ordering = ("-registered_at",)
        constraints = (
            models.UniqueConstraint(
                models.F("event"),
                Lower("email"),
                name="event_registrations_email_unique_case_insensitive",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()

    def __str__(self) -> str:
        return f"{self.event.title} - {self.email}"


class EventAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(
        EventRegistration,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        EventQuestion,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_answers"
        ordering = ("question__display_order",)
        constraints = (
            models.UniqueConstraint(
                fields=("registration", "question"),
                name="event_answers_question_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.registration_id
            and self.question_id
            and self.registration.event_id != self.question.event_id
        ):
            raise ValidationError(
                {"question": "The question must belong to the same event."}
            )


class EventTicket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.OneToOneField(
        EventRegistration,
        on_delete=models.PROTECT,
        related_name="ticket",
    )
    qr_code_hash = models.CharField(max_length=64, unique=True, editable=False)
    delivery_status = models.CharField(
        max_length=16,
        choices=QrDeliveryStatus.choices,
        default=QrDeliveryStatus.PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivery_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_tickets"

    def __str__(self) -> str:
        return f"Ticket for {self.registration.email}"


class EventScanner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="scanners",
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="event_scanner_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_event_scanners",
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_scanners"
        ordering = ("event__starts_at", "assigned_at")
        constraints = (
            models.UniqueConstraint(
                fields=("event", "membership"),
                name="event_scanners_membership_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if self.membership_id and (
            self.membership.status != MembershipStatus.ACTIVE
            or not self.membership.user.is_active
        ):
            raise ValidationError(
                {"membership": "The scanner must be an active member."}
            )

    def __str__(self) -> str:
        return f"{self.event.title} - {self.membership.user.email}"


class EventCheckIn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(
        EventTicket,
        on_delete=models.PROTECT,
        related_name="check_in",
    )
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="event_check_ins",
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "event_check_ins"
        ordering = ("-checked_in_at",)

    def __str__(self) -> str:
        return f"Check-in for {self.ticket.registration.email}"
