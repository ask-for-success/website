import hashlib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.permissions import is_hr_manager
from apps.memberships.models import Membership, MembershipStatus
from apps.memberships.operations import (
    create_initial_membership,
    reactivate_membership_after_acceptance,
)

from .models import (
    ApplicationCv,
    ApplicationStatus,
    DecisionEmailStatus,
    RecruitmentAnswer,
    RecruitmentApplication,
    RecruitmentOpportunity,
    RecruitmentQuestionType,
)


FINAL_APPLICATION_STATUSES = {
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
}
MAX_CV_SIZE = 10 * 1024 * 1024


def _is_empty(value) -> bool:
    return value is None or value == "" or value == []


def _validate_answer(question, value):
    question_type = question.question_type
    if question_type in {
        RecruitmentQuestionType.SHORT_TEXT,
        RecruitmentQuestionType.LONG_TEXT,
        RecruitmentQuestionType.EMAIL,
        RecruitmentQuestionType.PHONE,
    }:
        if not isinstance(value, str):
            raise ValidationError("The answer must be text.")
        value = value.strip()
        if question_type == RecruitmentQuestionType.EMAIL:
            validate_email(value)
        return value

    if question_type == RecruitmentQuestionType.YES_NO:
        if not isinstance(value, bool):
            raise ValidationError("The answer must be true or false.")
        return value

    option_ids = {
        str(option_id)
        for option_id in question.options.values_list("id", flat=True)
    }
    if question_type == RecruitmentQuestionType.SINGLE_CHOICE:
        value = str(value)
        if value not in option_ids:
            raise ValidationError("The selected option is invalid.")
        return value

    if question_type == RecruitmentQuestionType.MULTIPLE_CHOICE:
        if not isinstance(value, list):
            raise ValidationError("The answer must be a list of options.")
        values = [str(item) for item in value]
        if len(values) != len(set(values)):
            raise ValidationError("An option cannot be selected more than once.")
        if not set(values).issubset(option_ids):
            raise ValidationError("A selected option is invalid.")
        return values

    raise ValidationError("This question type is not supported.")


def _prepare_answers(opportunity: RecruitmentOpportunity, answers):
    if not isinstance(answers, list):
        raise ValidationError({"answers": "Answers must be a JSON list."})

    questions = {
        str(question.id): question
        for question in opportunity.form.questions.prefetch_related("options")
    }
    answers_by_question = {}
    errors = {}

    for position, answer in enumerate(answers):
        if not isinstance(answer, dict):
            errors[str(position)] = "Each answer must be an object."
            continue
        question_id = str(answer.get("question_id", ""))
        if question_id in answers_by_question:
            errors[str(position)] = "This question has more than one answer."
            continue
        question = questions.get(question_id)
        if question is None:
            errors[str(position)] = (
                "This question does not belong to the application form."
            )
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


def validate_cv_file(cv_file) -> None:
    if cv_file.size > MAX_CV_SIZE:
        raise ValidationError({"cv": "The CV must not exceed 10 MB."})
    if Path(cv_file.name).suffix.lower() != ".pdf":
        raise ValidationError({"cv": "The CV must be a PDF file."})

    position = cv_file.tell()
    signature = cv_file.read(5)
    cv_file.seek(position)
    if signature != b"%PDF-":
        raise ValidationError({"cv": "The uploaded file is not a valid PDF."})


def _file_sha256(cv_file) -> str:
    digest = hashlib.sha256()
    cv_file.seek(0)
    for chunk in cv_file.chunks():
        digest.update(chunk)
    cv_file.seek(0)
    return digest.hexdigest()


def create_recruitment_application(
    *,
    opportunity: RecruitmentOpportunity,
    applicant,
    answers,
    cv_file,
) -> RecruitmentApplication:
    if not applicant.is_active:
        raise ValidationError({"applicant": "The applicant account is inactive."})
    if not opportunity.accepts_applications():
        raise ValidationError(
            {"opportunity": "Applications are not open for this opportunity."}
        )

    validate_cv_file(cv_file)
    prepared_answers = _prepare_answers(opportunity, answers)
    saved_cv = None
    try:
        with transaction.atomic():
            locked_applicant = User.objects.select_for_update().get(pk=applicant.pk)
            application = RecruitmentApplication.objects.create(
                opportunity=opportunity,
                applicant=locked_applicant,
            )
            for question, value in prepared_answers:
                answer = RecruitmentAnswer(
                    application=application,
                    question=question,
                    value=value,
                )
                answer.full_clean()
                answer.save()

            saved_cv = ApplicationCv(
                application=application,
                file=cv_file,
                original_filename=Path(cv_file.name).name,
                content_type="application/pdf",
                size=cv_file.size,
                sha256=_file_sha256(cv_file),
            )
            saved_cv.full_clean(exclude=("file",))
            saved_cv.save()
    except IntegrityError as error:
        if saved_cv and saved_cv.file.name:
            saved_cv.file.storage.delete(saved_cv.file.name)
        raise ValidationError(
            {"opportunity": "You already applied to this opportunity."}
        ) from error
    except Exception:
        if saved_cv and saved_cv.file.name:
            saved_cv.file.storage.delete(saved_cv.file.name)
        raise
    return application


@transaction.atomic
def change_application_status(
    *,
    application: RecruitmentApplication,
    new_status: str,
    changed_by,
) -> RecruitmentApplication:
    if not is_hr_manager(changed_by):
        raise ValidationError(
            {"permission": "HR permission is required to change application status."}
        )

    locked_application = (
        RecruitmentApplication.objects.select_for_update()
        .select_related(
            "applicant",
            "opportunity__form__department",
            "opportunity__form__position",
        )
        .get(pk=application.pk)
    )
    if locked_application.status in FINAL_APPLICATION_STATUSES:
        raise ValidationError(
            {"status": "A final application decision cannot be changed."}
        )
    if new_status == locked_application.status:
        return locked_application

    if new_status in FINAL_APPLICATION_STATUSES:
        locked_applicant = User.objects.select_for_update().get(
            pk=locked_application.applicant_id
        )
        if new_status == ApplicationStatus.ACCEPTED:
            membership = (
                Membership.objects.select_for_update()
                .filter(user=locked_applicant)
                .first()
            )
            form = locked_application.opportunity.form
            if membership is None:
                create_initial_membership(
                    user=locked_applicant,
                    department=form.department,
                    position=form.position,
                    assigned_by=changed_by,
                )
            elif membership.status == MembershipStatus.INACTIVE:
                reactivate_membership_after_acceptance(
                    membership=membership,
                    department=form.department,
                    position=form.position,
                    assigned_by=changed_by,
                )
            else:
                raise ValidationError(
                    {
                        "status": (
                            "This applicant already has a pending or active "
                            "membership. Use the explicit transfer workflow."
                        )
                    }
                )

        locked_application.decision_by = changed_by
        locked_application.decided_at = timezone.now()
        locked_application.decision_email_status = DecisionEmailStatus.PENDING
        locked_application.decision_email_error = ""

    locked_application.status = new_status
    locked_application.save(
        update_fields=(
            "status",
            "decision_by",
            "decided_at",
            "decision_email_status",
            "decision_email_error",
            "updated_at",
        )
    )
    return locked_application


def send_application_decision_email(application: RecruitmentApplication) -> None:
    if (
        application.status not in FINAL_APPLICATION_STATUSES
        or application.decision_email_status != DecisionEmailStatus.PENDING
    ):
        return

    accepted = application.status == ApplicationStatus.ACCEPTED
    subject = (
        "Your application was accepted"
        if accepted
        else "Update on your application"
    )
    body = (
        (
            f"Your application for {application.opportunity.title} was accepted.\n\n"
            + (
                "Your membership has been reactivated. Log in to your account "
                "to view your current department and position."
                if application.applicant.membership.status
                == MembershipStatus.ACTIVE
                else "Log in to your account to continue membership onboarding."
            )
        )
        if accepted
        else (
            f"Your application for {application.opportunity.title} was not "
            "selected. Thank you for your interest in Ask For Success."
        )
    )
    try:
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.applicant.email],
        )
        sent_count = message.send(fail_silently=False)
        if sent_count != 1:
            raise RuntimeError("The email service did not confirm delivery.")
    except Exception as error:
        application.decision_email_status = DecisionEmailStatus.FAILED
        application.decision_email_error = str(error)[:2000]
        application.save(
            update_fields=(
                "decision_email_status",
                "decision_email_error",
                "updated_at",
            )
        )
        return

    application.decision_email_status = DecisionEmailStatus.SENT
    application.decision_email_sent_at = timezone.now()
    application.decision_email_error = ""
    application.save(
        update_fields=(
            "decision_email_status",
            "decision_email_sent_at",
            "decision_email_error",
            "updated_at",
        )
    )
