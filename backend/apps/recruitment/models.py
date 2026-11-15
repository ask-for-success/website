import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.organization.models import Department, Position

from .storage import private_media_storage


class RecruitmentFormStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class RecruitmentQuestionType(models.TextChoices):
    SHORT_TEXT = "short_text", "Short text"
    LONG_TEXT = "long_text", "Long text"
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"
    SINGLE_CHOICE = "single_choice", "Single choice"
    MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
    YES_NO = "yes_no", "Yes or no"


class OpportunityStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    CLOSED = "closed", "Closed"
    ARCHIVED = "archived", "Archived"


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under review"
    CONTACTED = "contacted", "Contacted"
    INTERVIEW = "interview", "Interview"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class DecisionEmailStatus(models.TextChoices):
    NOT_REQUIRED = "not_required", "Not required"
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class RecruitmentForm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="recruitment_forms",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="recruitment_forms",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=RecruitmentFormStatus.choices,
        default=RecruitmentFormStatus.DRAFT,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_recruitment_forms",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruitment_forms"
        ordering = ("department__name", "position__name", "name")
        constraints = (
            models.UniqueConstraint(
                models.F("department"),
                models.F("position"),
                Lower("name"),
                name="recruitment_forms_scope_name_unique_ci",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.description = self.description.strip()
        if (
            self.department_id
            and self.position_id
            and self.position.department_id != self.department_id
        ):
            raise ValidationError(
                {"position": "The position must belong to the selected department."}
            )

    def __str__(self) -> str:
        return self.name


class RecruitmentQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(
        RecruitmentForm,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    label = models.CharField(max_length=300)
    help_text = models.CharField(max_length=500, blank=True)
    question_type = models.CharField(
        max_length=32,
        choices=RecruitmentQuestionType.choices,
    )
    is_required = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruitment_questions"
        ordering = ("display_order", "created_at")
        constraints = (
            models.UniqueConstraint(
                fields=("form", "display_order"),
                name="recruitment_questions_order_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.label = self.label.strip()
        self.help_text = self.help_text.strip()

    def __str__(self) -> str:
        return self.label


class RecruitmentQuestionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        RecruitmentQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=200)
    display_order = models.PositiveIntegerField()

    class Meta:
        db_table = "recruitment_question_options"
        ordering = ("display_order", "id")
        constraints = (
            models.UniqueConstraint(
                fields=("question", "display_order"),
                name="recruitment_question_options_order_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.label = self.label.strip()
        if self.question_id and self.question.question_type not in {
            RecruitmentQuestionType.SINGLE_CHOICE,
            RecruitmentQuestionType.MULTIPLE_CHOICE,
        }:
            raise ValidationError(
                {"question": "Only choice questions can contain options."}
            )

    def __str__(self) -> str:
        return self.label


class RecruitmentOpportunity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(
        RecruitmentForm,
        on_delete=models.PROTECT,
        related_name="opportunities",
    )
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240)
    summary = models.TextField(max_length=500)
    description_markdown = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=OpportunityStatus.choices,
        default=OpportunityStatus.DRAFT,
    )
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_recruitment_opportunities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruitment_opportunities"
        ordering = ("-created_at",)
        constraints = (
            models.UniqueConstraint(
                Lower("slug"),
                name="recruitment_opportunities_slug_unique_ci",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.slug = self.slug.strip().lower()
        self.summary = self.summary.strip()
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            raise ValidationError(
                {"closes_at": "Applications must close after they open."}
            )

    def accepts_applications(self) -> bool:
        now = timezone.now()
        if self.status != OpportunityStatus.PUBLISHED:
            return False
        if self.form.status != RecruitmentFormStatus.ACTIVE:
            return False
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now >= self.closes_at:
            return False
        return True

    def __str__(self) -> str:
        return self.title


class RecruitmentApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        RecruitmentOpportunity,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recruitment_applications",
    )
    status = models.CharField(
        max_length=24,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="decided_recruitment_applications",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_email_status = models.CharField(
        max_length=16,
        choices=DecisionEmailStatus.choices,
        default=DecisionEmailStatus.NOT_REQUIRED,
    )
    decision_email_sent_at = models.DateTimeField(null=True, blank=True)
    decision_email_error = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruitment_applications"
        ordering = ("-submitted_at",)
        constraints = (
            models.UniqueConstraint(
                fields=("opportunity", "applicant"),
                name="recruitment_applications_applicant_unique",
            ),
        )

    def __str__(self) -> str:
        return f"{self.applicant.email} — {self.opportunity.title}"


class RecruitmentAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        RecruitmentApplication,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        RecruitmentQuestion,
        on_delete=models.PROTECT,
        related_name="answers",
    )
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recruitment_answers"
        ordering = ("question__display_order",)
        constraints = (
            models.UniqueConstraint(
                fields=("application", "question"),
                name="recruitment_answers_question_unique",
            ),
        )

    def clean(self) -> None:
        super().clean()
        if (
            self.application_id
            and self.question_id
            and self.application.opportunity.form_id != self.question.form_id
        ):
            raise ValidationError(
                {"question": "The question must belong to the application form."}
            )


def cv_upload_path(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return (
        f"recruitment/cvs/{instance.application_id}/"
        f"{uuid.uuid4().hex}{extension}"
    )


class ApplicationCv(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        RecruitmentApplication,
        on_delete=models.CASCADE,
        related_name="cv",
    )
    file = models.FileField(
        storage=private_media_storage,
        upload_to=cv_upload_path,
        max_length=500,
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_cvs"

    def __str__(self) -> str:
        return self.original_filename
