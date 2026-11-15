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
from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event
from apps.memberships.models import Membership, MembershipStatus
from apps.memberships.operations import (
    create_initial_membership,
    reactivate_membership_after_acceptance,
)

from .models import (
    ApplicationCv,
    ApplicationStatus,
    DecisionEmailStatus,
    OfferResponse,
    RecruitmentAnswer,
    RecruitmentApplication,
    RecruitmentOpportunity,
    RecruitmentQuestionType,
)


FINAL_APPLICATION_STATUSES = {
    ApplicationStatus.ACCEPTED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.DECLINED_BY_CANDIDATE,
    ApplicationStatus.WITHDRAWN,
}
HR_MANAGED_APPLICATION_STATUSES = {
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.CONTACTED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER_PENDING,
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
            if RecruitmentApplication.objects.filter(
                opportunity=opportunity,
                applicant=locked_applicant,
            ).exists():
                raise ValidationError(
                    {
                        "opportunity": (
                            "You already applied to this opportunity. Apply to "
                            "a new opportunity for a later recruitment campaign."
                        )
                    }
                )
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
            {
                "opportunity": (
                    "You already applied to this opportunity. Apply to a new "
                    "opportunity for a later recruitment campaign."
                )
            }
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
        RecruitmentApplication.objects.select_for_update(of=("self",))
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

    if new_status not in HR_MANAGED_APPLICATION_STATUSES:
        raise ValidationError(
            {
                "status": (
                    "HR can move an application through review, send an offer, "
                    "or reject it. Only the candidate can accept or decline an "
                    "offer."
                )
            }
        )
    if locked_application.status == ApplicationStatus.OFFER_PENDING:
        raise ValidationError(
            {"status": "The candidate must respond to the outstanding offer."}
        )

    previous_status = locked_application.status
    now = timezone.now()
    if new_status == ApplicationStatus.OFFER_PENDING:
        locked_application.offer_by = changed_by
        locked_application.offered_at = now
        locked_application.offer_email_status = DecisionEmailStatus.PENDING
        locked_application.offer_email_error = ""
    elif new_status == ApplicationStatus.REJECTED:
        locked_application.decision_by = changed_by
        locked_application.decided_at = now
        locked_application.decision_email_status = DecisionEmailStatus.PENDING
        locked_application.decision_email_error = ""

    locked_application.status = new_status
    locked_application.save(
        update_fields=(
            "status",
            "offer_by",
            "offered_at",
            "offer_email_status",
            "offer_email_error",
            "decision_by",
            "decided_at",
            "decision_email_status",
            "decision_email_error",
            "updated_at",
        )
    )
    record_audit_event(
        domain=AuditDomain.RECRUITMENT,
        action=AuditAction.APPLICATION_STATUS_CHANGED,
        actor=changed_by,
        application=locked_application,
        previous_state={"application_status": previous_status},
        new_state={"application_status": locked_application.status},
    )
    return locked_application


@transaction.atomic
def respond_to_application_offer(
    *,
    application: RecruitmentApplication,
    response: str,
    responded_by,
) -> RecruitmentApplication:
    if application.applicant_id != responded_by.id:
        raise ValidationError(
            {"permission": "Only the applicant can respond to this offer."}
        )
    locked_applicant = User.objects.select_for_update().get(pk=responded_by.pk)
    locked_application = (
        RecruitmentApplication.objects.select_for_update(of=("self",))
        .select_related(
            "applicant",
            "offer_by",
            "opportunity__form__department",
            "opportunity__form__position",
        )
        .get(pk=application.pk)
    )
    if locked_application.applicant_id != locked_applicant.id:
        raise ValidationError(
            {"permission": "Only the applicant can respond to this offer."}
        )
    if locked_application.status != ApplicationStatus.OFFER_PENDING:
        raise ValidationError(
            {"status": "This application does not have an outstanding offer."}
        )
    if response not in OfferResponse.values:
        raise ValidationError({"response": "The offer response is invalid."})
    if not locked_application.offer_by_id:
        raise ValidationError(
            {"offer": "The application offer has no authorized HR actor."}
        )

    now = timezone.now()
    previous_status = locked_application.status
    affected_membership = None

    if response == OfferResponse.ACCEPT:
        affected_membership = (
            Membership.objects.select_for_update()
            .filter(user=locked_applicant)
            .first()
        )
        form = locked_application.opportunity.form
        if affected_membership is None:
            affected_membership = create_initial_membership(
                user=locked_applicant,
                department=form.department,
                position=form.position,
                assigned_by=locked_application.offer_by,
                source_application=locked_application,
            )
        elif affected_membership.status == MembershipStatus.INACTIVE:
            affected_membership = reactivate_membership_after_acceptance(
                membership=affected_membership,
                department=form.department,
                position=form.position,
                assigned_by=locked_application.offer_by,
                source_application=locked_application,
            )

        locked_application.status = ApplicationStatus.ACCEPTED
        locked_application.decision_email_status = DecisionEmailStatus.PENDING
        locked_application.decision_email_error = ""
    else:
        locked_application.status = ApplicationStatus.DECLINED_BY_CANDIDATE
        locked_application.decision_email_status = (
            DecisionEmailStatus.NOT_REQUIRED
        )
        locked_application.decision_email_error = ""

    locked_application.offer_responded_at = now
    locked_application.decision_by = responded_by
    locked_application.decided_at = now
    locked_application.save(
        update_fields=(
            "status",
            "offer_responded_at",
            "decision_by",
            "decided_at",
            "decision_email_status",
            "decision_email_error",
            "updated_at",
        )
    )
    record_audit_event(
        domain=AuditDomain.RECRUITMENT,
        action=AuditAction.APPLICATION_STATUS_CHANGED,
        actor=responded_by,
        application=locked_application,
        membership=affected_membership,
        previous_state={"application_status": previous_status},
        new_state={"application_status": locked_application.status},
    )

    if response == OfferResponse.ACCEPT:
        other_applications = (
            RecruitmentApplication.objects.select_for_update()
            .filter(applicant_id=locked_application.applicant_id)
            .exclude(pk=locked_application.pk)
            .exclude(status__in=FINAL_APPLICATION_STATUSES)
        )
        for other_application in other_applications:
            other_previous_status = other_application.status
            other_application.status = ApplicationStatus.WITHDRAWN
            other_application.decision_by = responded_by
            other_application.decided_at = now
            other_application.decision_email_status = (
                DecisionEmailStatus.NOT_REQUIRED
            )
            other_application.decision_email_error = ""
            other_application.save(
                update_fields=(
                    "status",
                    "decision_by",
                    "decided_at",
                    "decision_email_status",
                    "decision_email_error",
                    "updated_at",
                )
            )
            record_audit_event(
                domain=AuditDomain.RECRUITMENT,
                action=AuditAction.APPLICATION_STATUS_CHANGED,
                actor=responded_by,
                application=other_application,
                membership=affected_membership,
                previous_state={
                    "application_status": other_previous_status
                },
                new_state={
                    "application_status": ApplicationStatus.WITHDRAWN
                },
            )

    return locked_application


def _accepted_email_body(application: RecruitmentApplication) -> str:
    membership = application.applicant.membership
    form = application.opportunity.form
    current_assignment = membership.assignments.filter(
        ends_at__isnull=True
    ).first()
    requires_transfer = bool(
        current_assignment
        and (
            current_assignment.department_id != form.department_id
            or current_assignment.position_id != form.position_id
        )
    )
    if requires_transfer:
        next_step = (
            "Your response was recorded. HR will complete the explicit department "
            "transfer before the new assignment becomes active."
        )
    elif membership.status == MembershipStatus.ACTIVE:
        next_step = (
            "Your membership is active. Log in to view your current department "
            "and position."
        )
    else:
        next_step = "Log in to your account to continue membership onboarding."
    return (
        f"You accepted the offer for {application.opportunity.title}.\n\n"
        f"{next_step}"
    )


def send_application_status_email(application: RecruitmentApplication) -> None:
    if (
        application.status == ApplicationStatus.OFFER_PENDING
        and application.offer_email_status == DecisionEmailStatus.PENDING
    ):
        email_kind = "offer"
        subject = f"Offer for {application.opportunity.title}"
        body = (
            f"You received an offer for {application.opportunity.title}.\n\n"
            "Log in to your account to accept or decline the offer. No membership "
            "will be created until you accept."
        )
    elif (
        application.status == ApplicationStatus.REJECTED
        and application.decision_email_status == DecisionEmailStatus.PENDING
    ):
        email_kind = "decision"
        subject = "Update on your application"
        body = (
            f"Your application for {application.opportunity.title} was not "
            "selected. Thank you for your interest in Ask For Success."
        )
    elif (
        application.status == ApplicationStatus.ACCEPTED
        and application.decision_email_status == DecisionEmailStatus.PENDING
    ):
        email_kind = "decision"
        subject = "Your offer was accepted"
        body = _accepted_email_body(application)
    else:
        return

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
        if email_kind == "offer":
            application.offer_email_status = DecisionEmailStatus.FAILED
            application.offer_email_error = str(error)[:2000]
            application.save(
                update_fields=(
                    "offer_email_status",
                    "offer_email_error",
                    "updated_at",
                )
            )
        else:
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

    if email_kind == "offer":
        application.offer_email_status = DecisionEmailStatus.SENT
        application.offer_email_sent_at = timezone.now()
        application.offer_email_error = ""
        application.save(
            update_fields=(
                "offer_email_status",
                "offer_email_sent_at",
                "offer_email_error",
                "updated_at",
            )
        )
    else:
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
