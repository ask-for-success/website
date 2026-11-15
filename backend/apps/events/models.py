import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.memberships.models import Membership, MembershipStatus


MAX_EVENT_IMAGE_SIZE = 10 * 1024 * 1024


def validate_event_image_size(image) -> None:
    if image.size > MAX_EVENT_IMAGE_SIZE:
        raise ValidationError("The image must not exceed 10 MB.")


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    CANCELLED = "cancelled", "Cancelled"
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


class EventRegistrationSource(models.TextChoices):
    PUBLIC = "public", "Public"
    MANUAL = "manual", "Manual"


class RegistrationCancellationSource(models.TextChoices):
    SELF_SERVICE = "self_service", "Self-service"
    EVENT_CANCELLED = "event_cancelled", "Event cancelled"


class QrDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class EmailDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class EventNotificationType(models.TextChoices):
    CONFIRMATION = "confirmation", "Confirmation"
    RESCHEDULED = "rescheduled", "Rescheduled"
    CANCELLED = "cancelled", "Cancelled"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    description = models.TextField()
    cover_image = models.ImageField(
        upload_to="events/covers/%Y/%m/",
        validators=(validate_event_image_size,),
        null=True,
        blank=True,
    )
    cover_alt_text = models.CharField(max_length=250, blank=True)
    location = models.CharField(max_length=255)
    attendance_label = models.CharField(max_length=100, default="Free")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    requires_qr_code = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cancelled_events",
    )
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
        self.cover_alt_text = self.cover_alt_text.strip()
        self.attendance_label = self.attendance_label.strip()
        if self.cover_image and not self.cover_alt_text:
            raise ValidationError(
                {"cover_alt_text": "Alternative text is required."}
            )
        if self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "The end time must be after the start time."}
            )
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError(
                {"capacity": "Capacity must be at least one."}
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

    def active_registration_count(self) -> int:
        return self.registrations.filter(
            status=EventRegistrationStatus.REGISTERED
        ).count()

    def seats_remaining(self) -> int | None:
        if self.capacity is None:
            return None
        return max(self.capacity - self.active_registration_count(), 0)

    def is_registration_full(self) -> bool:
        remaining = self.seats_remaining()
        return remaining is not None and remaining == 0

    def accepts_registrations(self) -> bool:
        now = timezone.now()
        if self.publication_status != PublicationStatus.PUBLISHED:
            return False
        if self.registration_opens_at and now < self.registration_opens_at:
            return False
        closes_at = self.registration_closes_at or self.starts_at
        return now < closes_at and not self.is_registration_full()

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
    source = models.CharField(
        max_length=16,
        choices=EventRegistrationSource.choices,
        default=EventRegistrationSource.PUBLIC,
    )
    confirmation_email_status = models.CharField(
        max_length=16,
        choices=EmailDeliveryStatus.choices,
        default=EmailDeliveryStatus.PENDING,
    )
    confirmation_email_sent_at = models.DateTimeField(null=True, blank=True)
    confirmation_email_error = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_source = models.CharField(
        max_length=24,
        choices=RegistrationCancellationSource.choices,
        blank=True,
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
        indexes = (
            models.Index(
                fields=("event", "status"),
                name="event_registration_status_idx",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.email = self.email.strip().lower()

    def __str__(self) -> str:
        return f"{self.event.title} - {self.email}"

    @property
    def cancellation_deadline(self):
        return self.event.starts_at - timedelta(hours=24)


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


class EventParticipantNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="participant_notifications",
    )
    registration = models.ForeignKey(
        EventRegistration,
        on_delete=models.PROTECT,
        related_name="participant_notifications",
    )
    notification_type = models.CharField(
        max_length=16,
        choices=EventNotificationType.choices,
    )
    delivery_status = models.CharField(
        max_length=16,
        choices=EmailDeliveryStatus.choices,
        default=EmailDeliveryStatus.PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivery_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event_participant_notifications"
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(
                fields=("event", "notification_type", "created_at"),
                name="event_notification_type_idx",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.event_id
            and self.registration_id
            and self.registration.event_id != self.event_id
        ):
            raise ValidationError(
                {"registration": "The registration must belong to the event."}
            )

    def __str__(self) -> str:
        return (
            f"{self.get_notification_type_display()} - "
            f"{self.registration.email}"
        )


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
