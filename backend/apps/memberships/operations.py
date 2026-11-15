import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.permissions import is_hr_manager
from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event
from apps.organization.models import Department, Position

from .models import (
    MemberAssignment,
    MemberIdentity,
    Membership,
    MembershipInvitation,
    MembershipInvitationStatus,
    MembershipOnboarding,
    MembershipStatus,
    OnboardingStatus,
)


INVITATION_LIFETIME = timedelta(hours=48)


@dataclass(frozen=True)
class MembershipInvitationResult:
    invitation: MembershipInvitation
    setup_token: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_hr_manager(user) -> None:
    if not is_hr_manager(user):
        raise PermissionDenied(
            "This operation requires content-manager access and HR permission."
        )


def ensure_position_department(
    position: Position,
    department: Department,
) -> None:
    if not department.is_active:
        raise ValidationError(
            {"department": "The selected department is inactive."}
        )
    if not position.is_active:
        raise ValidationError(
            {"position": "The selected position is inactive."}
        )
    if position.department_id != department.id:
        raise ValidationError(
            {"position": "The position must belong to the selected department."}
        )


@transaction.atomic
def create_initial_membership(
    *,
    user,
    department: Department,
    position: Position,
    assigned_by,
    source_application=None,
) -> Membership:
    ensure_hr_manager(assigned_by)
    ensure_position_department(position, department)

    locked_user = User.objects.select_for_update().get(pk=user.pk)
    if Membership.objects.filter(user=locked_user).exists():
        raise ValidationError(
            {"user": "This user already has a membership."}
        )

    membership = Membership.objects.create(user=locked_user)
    MembershipOnboarding.objects.create(membership=membership)
    assignment = MemberAssignment(
        membership=membership,
        department=department,
        position=position,
        assigned_by=assigned_by,
    )
    assignment.full_clean()
    assignment.save()
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.MEMBERSHIP_CREATED,
        actor=assigned_by,
        application=source_application,
        membership=membership,
        new_state={
            "membership_status": membership.status,
            "onboarding_status": membership.onboarding.status,
            "department_id": str(department.id),
            "position_id": str(position.id),
            "assignment_id": str(assignment.id),
        },
    )
    return membership


def admit_existing_account(
    *,
    user: User,
    department: Department,
    position: Position,
    admitted_by,
) -> Membership:
    if not user.is_active:
        raise ValidationError(
            {"user": "An existing account must be active before admission."}
        )
    return create_initial_membership(
        user=user,
        department=department,
        position=position,
        assigned_by=admitted_by,
    )


@transaction.atomic
def transfer_member(
    *,
    membership: Membership,
    new_department: Department,
    new_position: Position,
    assigned_by,
    reason: str,
) -> MemberAssignment:
    ensure_hr_manager(assigned_by)
    ensure_position_department(new_position, new_department)

    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "A transfer reason is required."})

    locked_membership = Membership.objects.select_for_update().get(
        pk=membership.pk
    )
    if locked_membership.status == MembershipStatus.INACTIVE:
        raise ValidationError(
            {"membership": "An inactive membership cannot be transferred."}
        )
    try:
        current_assignment = MemberAssignment.objects.select_for_update().get(
            membership=locked_membership,
            ends_at__isnull=True,
        )
    except MemberAssignment.DoesNotExist as error:
        raise ValidationError(
            {"membership": "No active assignment can be replaced."}
        ) from error

    if (
        current_assignment.department_id == new_department.id
        and current_assignment.position_id == new_position.id
    ):
        raise ValidationError(
            {"assignment": "The new assignment must be different."}
        )

    now = timezone.now()
    previous_state = {
        "membership_status": locked_membership.status,
        "department_id": str(current_assignment.department_id),
        "position_id": str(current_assignment.position_id),
        "assignment_id": str(current_assignment.id),
    }
    current_assignment.ends_at = now
    current_assignment.end_reason = reason
    current_assignment.save(
        update_fields=("ends_at", "end_reason", "updated_at")
    )

    new_assignment = MemberAssignment(
        membership=locked_membership,
        department=new_department,
        position=new_position,
        assigned_by=assigned_by,
        starts_at=now,
    )
    new_assignment.full_clean()
    new_assignment.save()
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.MEMBERSHIP_TRANSFERRED,
        actor=assigned_by,
        membership=locked_membership,
        previous_state=previous_state,
        new_state={
            "membership_status": locked_membership.status,
            "department_id": str(new_department.id),
            "position_id": str(new_position.id),
            "assignment_id": str(new_assignment.id),
        },
        reason=reason,
    )
    return new_assignment


@transaction.atomic
def update_onboarding_status(
    *,
    membership: Membership,
    new_status: str,
    updated_by,
) -> MembershipOnboarding:
    ensure_hr_manager(updated_by)

    locked_membership = Membership.objects.select_for_update().select_related(
        "user"
    ).get(pk=membership.pk)
    if locked_membership.status == MembershipStatus.INACTIVE:
        raise ValidationError(
            {"membership": "An inactive membership cannot continue onboarding."}
        )
    if not locked_membership.user.is_active:
        raise ValidationError(
            {
                "membership": (
                    "The invited account must be set up before onboarding starts."
                )
            }
        )

    onboarding = MembershipOnboarding.objects.select_for_update().get(
        membership=locked_membership
    )
    now = timezone.now()
    previous_state = {
        "membership_status": locked_membership.status,
        "onboarding_status": onboarding.status,
    }

    if new_status == OnboardingStatus.IN_PROGRESS:
        if onboarding.status == OnboardingStatus.COMPLETED:
            raise ValidationError(
                {"status": "Completed onboarding cannot be reopened."}
            )
        if onboarding.status == OnboardingStatus.NOT_STARTED:
            onboarding.status = OnboardingStatus.IN_PROGRESS
            onboarding.started_at = now
            onboarding.save(
                update_fields=("status", "started_at", "updated_at")
            )
            record_audit_event(
                domain=AuditDomain.MEMBERSHIP,
                action=AuditAction.ONBOARDING_STATUS_CHANGED,
                actor=updated_by,
                membership=locked_membership,
                previous_state=previous_state,
                new_state={
                    "membership_status": locked_membership.status,
                    "onboarding_status": onboarding.status,
                },
            )
        return onboarding

    raise ValidationError(
        {
            "status": (
                "HR can mark onboarding as in progress, but only the member can "
                "complete their own onboarding."
            )
        }
    )


@transaction.atomic
def complete_self_onboarding(
    *,
    user: User,
    national_id_number: str,
) -> Membership:
    try:
        locked_membership = (
            Membership.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(user=user)
        )
    except Membership.DoesNotExist as error:
        raise ValidationError(
            {"membership": "This account does not have an accepted membership."}
        ) from error

    if not locked_membership.user.is_active:
        raise ValidationError(
            {"membership": "The account must be active before onboarding."}
        )
    if locked_membership.status == MembershipStatus.INACTIVE:
        raise ValidationError(
            {"membership": "An inactive membership cannot complete onboarding."}
        )
    if locked_membership.status == MembershipStatus.ACTIVE:
        raise ValidationError(
            {"membership": "This membership is already active."}
        )

    onboarding = MembershipOnboarding.objects.select_for_update().get(
        membership=locked_membership
    )
    if onboarding.status == OnboardingStatus.COMPLETED:
        raise ValidationError({"onboarding": "Onboarding is already complete."})
    if MemberIdentity.objects.filter(membership=locked_membership).exists():
        raise ValidationError(
            {"national_id_number": "National ID was already submitted."}
        )

    normalized_number = national_id_number.strip().upper()
    if MemberIdentity.objects.filter(
        national_id_number=normalized_number
    ).exists():
        raise ValidationError(
            {
                "national_id_number": (
                    "This national ID number is already registered."
                )
            }
        )

    identity = MemberIdentity(
        membership=locked_membership,
        national_id_number=normalized_number,
    )
    identity.full_clean()
    try:
        identity.save()
    except IntegrityError as error:
        raise ValidationError(
            {
                "national_id_number": (
                    "This national ID number is already registered."
                )
            }
        ) from error

    now = timezone.now()
    previous_state = {
        "membership_status": locked_membership.status,
        "onboarding_status": onboarding.status,
        "national_id_collected": False,
    }
    if onboarding.started_at is None:
        onboarding.started_at = now
    onboarding.status = OnboardingStatus.COMPLETED
    onboarding.completed_at = now
    onboarding.save(
        update_fields=(
            "status",
            "started_at",
            "completed_at",
            "updated_at",
        )
    )
    locked_membership.status = MembershipStatus.ACTIVE
    locked_membership.save(update_fields=("status", "updated_at"))

    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.NATIONAL_ID_SUBMITTED,
        actor=user,
        membership=locked_membership,
        previous_state={"national_id_collected": False},
        new_state={"national_id_collected": True},
    )
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.ONBOARDING_STATUS_CHANGED,
        actor=user,
        membership=locked_membership,
        previous_state=previous_state,
        new_state={
            "membership_status": locked_membership.status,
            "onboarding_status": onboarding.status,
            "national_id_collected": True,
        },
    )
    return locked_membership


@transaction.atomic
def record_member_departure(
    *,
    membership: Membership,
    recorded_by,
    reason: str,
) -> Membership:
    ensure_hr_manager(recorded_by)

    reason = reason.strip()
    if not reason:
        raise ValidationError({"reason": "A departure reason is required."})

    locked_membership = Membership.objects.select_for_update().get(
        pk=membership.pk
    )
    if locked_membership.status != MembershipStatus.ACTIVE:
        raise ValidationError(
            {"membership": "Only an active membership can record a departure."}
        )
    try:
        current_assignment = MemberAssignment.objects.select_for_update().get(
            membership=locked_membership,
            ends_at__isnull=True,
        )
    except MemberAssignment.DoesNotExist as error:
        raise ValidationError(
            {"membership": "The active membership has no current assignment."}
        ) from error

    now = timezone.now()
    previous_state = {
        "membership_status": locked_membership.status,
        "department_id": str(current_assignment.department_id),
        "position_id": str(current_assignment.position_id),
        "assignment_id": str(current_assignment.id),
    }
    current_assignment.ends_at = now
    current_assignment.end_reason = reason
    current_assignment.save(
        update_fields=("ends_at", "end_reason", "updated_at")
    )
    locked_membership.status = MembershipStatus.INACTIVE
    locked_membership.save(update_fields=("status", "updated_at"))
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.DEPARTURE_RECORDED,
        actor=recorded_by,
        membership=locked_membership,
        previous_state=previous_state,
        new_state={"membership_status": locked_membership.status},
        reason=reason,
    )
    return locked_membership


@transaction.atomic
def reactivate_membership_after_acceptance(
    *,
    membership: Membership,
    department: Department,
    position: Position,
    assigned_by,
    source_application=None,
) -> Membership:
    ensure_hr_manager(assigned_by)
    ensure_position_department(position, department)

    locked_membership = Membership.objects.select_for_update().get(
        pk=membership.pk
    )
    if locked_membership.status != MembershipStatus.INACTIVE:
        raise ValidationError(
            {"membership": "Only an inactive membership can be reactivated."}
        )
    if MemberAssignment.objects.filter(
        membership=locked_membership,
        ends_at__isnull=True,
    ).exists():
        raise ValidationError(
            {"membership": "The inactive membership already has an assignment."}
        )
    if locked_membership.onboarding.status != OnboardingStatus.COMPLETED:
        raise ValidationError(
            {
                "membership": (
                    "A former member must have completed onboarding before "
                    "reactivation."
                )
            }
        )

    assignment = MemberAssignment(
        membership=locked_membership,
        department=department,
        position=position,
        assigned_by=assigned_by,
    )
    assignment.full_clean()
    assignment.save()
    previous_state = {"membership_status": locked_membership.status}
    locked_membership.status = MembershipStatus.ACTIVE
    locked_membership.save(update_fields=("status", "updated_at"))
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.MEMBERSHIP_REACTIVATED,
        actor=assigned_by,
        application=source_application,
        membership=locked_membership,
        previous_state=previous_state,
        new_state={
            "membership_status": locked_membership.status,
            "onboarding_status": locked_membership.onboarding.status,
            "department_id": str(department.id),
            "position_id": str(position.id),
            "assignment_id": str(assignment.id),
        },
    )
    return locked_membership


@transaction.atomic
def create_membership_invitation(
    *,
    email: str,
    first_name: str,
    last_name: str,
    department: Department,
    position: Position,
    created_by,
) -> MembershipInvitationResult:
    ensure_hr_manager(created_by)
    ensure_position_department(position, department)

    email = User.objects.normalize_email(email).lower()
    first_name = first_name.strip()
    last_name = last_name.strip()
    errors = {}
    if not email:
        errors["email"] = "Email is required."
    if not first_name:
        errors["first_name"] = "First name is required."
    if not last_name:
        errors["last_name"] = "Last name is required."
    if errors:
        raise ValidationError(errors)

    user = (
        User.objects.select_for_update()
        .filter(email__iexact=email)
        .first()
    )
    if user is None:
        user = User.objects.create_user(
            email=email,
            password=None,
            first_name=first_name,
            last_name=last_name,
            phone_number=None,
            is_active=False,
        )
        membership = create_initial_membership(
            user=user,
            department=department,
            position=position,
            assigned_by=created_by,
        )
    else:
        if user.is_active:
            raise ValidationError(
                {
                    "email": (
                        "This account already exists. Use the existing-account "
                        "admission workflow."
                    )
                }
            )
        if user.has_usable_password() or not MembershipInvitation.objects.filter(
            user=user
        ).exists():
            raise ValidationError(
                {
                    "email": (
                        "This inactive account was not created by a membership "
                        "invitation."
                    )
                }
            )

        try:
            membership = Membership.objects.select_for_update().get(user=user)
            assignment = MemberAssignment.objects.get(
                membership=membership,
                ends_at__isnull=True,
            )
        except (Membership.DoesNotExist, MemberAssignment.DoesNotExist) as error:
            raise ValidationError(
                {"email": "The invited account has incomplete membership data."}
            ) from error

        if (
            assignment.department_id != department.id
            or assignment.position_id != position.id
        ):
            raise ValidationError(
                {
                    "position": (
                        "A reissued invitation must keep the original assignment."
                    )
                }
            )

        user.first_name = first_name
        user.last_name = last_name
        user.full_clean()
        user.save(update_fields=("first_name", "last_name", "updated_at"))

    now = timezone.now()
    MembershipInvitation.objects.filter(
        user=user,
        status=MembershipInvitationStatus.ACTIVE,
    ).update(
        status=MembershipInvitationStatus.CANCELLED,
        cancelled_at=now,
        updated_at=now,
    )

    setup_token = secrets.token_urlsafe(32)
    invitation = MembershipInvitation(
        membership=membership,
        user=user,
        created_by=created_by,
        token_hash=_hash_token(setup_token),
        expires_at=now + INVITATION_LIFETIME,
    )
    invitation.full_clean()
    invitation.save()
    record_audit_event(
        domain=AuditDomain.MEMBERSHIP,
        action=AuditAction.INVITATION_CREATED,
        actor=created_by,
        membership=membership,
        new_state={"invitation_status": invitation.status},
    )
    return MembershipInvitationResult(
        invitation=invitation,
        setup_token=setup_token,
    )


def accept_membership_invitation(
    *,
    token: str,
    phone_number: str,
    password: str,
) -> User:
    deferred_error = None
    user = None

    with transaction.atomic():
        try:
            invitation = MembershipInvitation.objects.select_for_update().get(
                token_hash=_hash_token(token)
            )
        except MembershipInvitation.DoesNotExist as error:
            raise ValidationError(
                {"token": "This invitation is invalid or no longer usable."}
            ) from error

        if invitation.status != MembershipInvitationStatus.ACTIVE:
            raise ValidationError(
                {"token": "This invitation is invalid or no longer usable."}
            )

        now = timezone.now()
        if invitation.expires_at <= now:
            invitation.status = MembershipInvitationStatus.EXPIRED
            invitation.save(update_fields=("status", "updated_at"))
            deferred_error = ValidationError(
                {"token": "This invitation has expired."}
            )
        else:
            user = User.objects.select_for_update().get(pk=invitation.user_id)
            phone_number = phone_number.strip()
            if not phone_number:
                raise ValidationError(
                    {"phone_number": "Phone number is required."}
                )
            if User.objects.filter(phone_number=phone_number).exclude(
                pk=user.pk
            ).exists():
                raise ValidationError(
                    {"phone_number": "This phone number is already in use."}
                )

            try:
                password_validation.validate_password(password, user=user)
            except ValidationError as error:
                raise ValidationError(
                    {"password": list(error.messages)}
                ) from error

            user.phone_number = phone_number
            user.is_active = True
            user.set_password(password)
            user.full_clean()
            user.save(
                update_fields=(
                    "phone_number",
                    "is_active",
                    "password",
                    "updated_at",
                )
            )

            invitation.status = MembershipInvitationStatus.USED
            invitation.used_at = now
            invitation.save(
                update_fields=("status", "used_at", "updated_at")
            )
            record_audit_event(
                domain=AuditDomain.MEMBERSHIP,
                action=AuditAction.INVITATION_ACCEPTED,
                actor=user,
                membership=invitation.membership,
                previous_state={
                    "invitation_status": MembershipInvitationStatus.ACTIVE
                },
                new_state={"invitation_status": invitation.status},
            )

    if deferred_error:
        raise deferred_error
    return user
