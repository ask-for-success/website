import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.organization.models import Department, Position

from .models import (
    MemberAssignment,
    Membership,
    MembershipInvitation,
    MembershipInvitationStatus,
    MembershipOnboarding,
)


INVITATION_LIFETIME = timedelta(hours=48)


@dataclass(frozen=True)
class MembershipInvitationResult:
    invitation: MembershipInvitation
    setup_token: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_hr_manager(user) -> None:
    if user.is_superuser:
        return

    is_content_manager = user.groups.filter(name="content_manager").exists()
    has_hr_permission = user.has_perm("accounts.manage_hr")
    if not is_content_manager or not has_hr_permission:
        raise PermissionDenied(
            "This operation requires content-manager access and HR permission."
        )


def ensure_position_department(
    position: Position,
    department: Department,
) -> None:
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
) -> Membership:
    ensure_hr_manager(assigned_by)
    ensure_position_department(position, department)

    if Membership.objects.filter(user=user).exists():
        raise ValidationError(
            {"user": "This user already has a membership."}
        )

    membership = Membership.objects.create(user=user)
    MembershipOnboarding.objects.create(membership=membership)
    assignment = MemberAssignment(
        membership=membership,
        department=department,
        position=position,
        assigned_by=assigned_by,
    )
    assignment.full_clean()
    assignment.save()
    return membership


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
    return new_assignment


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

    if deferred_error:
        raise deferred_error
    return user
