import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.audit.models import AuditAction, AuditDomain
from apps.audit.services import record_audit_event

from .models import (
    AccountInvitation,
    AccountInvitationEmailStatus,
    AccountInvitationPurpose,
    AccountInvitationStatus,
    User,
)
from .roles import ACCOUNT_ADMINISTRATOR, CONTENT_MANAGER


INVITATION_LIFETIME = timedelta(hours=48)


@dataclass(frozen=True)
class AccountInvitationResult:
    invitation: AccountInvitation
    setup_token: str


def hash_setup_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_account_invitation_setup_link(setup_token: str) -> str:
    token = quote(setup_token, safe="")
    base_url = settings.PUBLIC_WEB_URL.rstrip("/")
    return f"{base_url}/account/invitation/setup?token={token}"


def account_access_state(user: User) -> dict:
    group_names = set(user.groups.values_list("name", flat=True))
    direct_permissions = set(
        user.user_permissions.filter(
            content_type__app_label="accounts",
        ).values_list("codename", flat=True)
    )
    return {
        "account_active": user.is_active,
        "account_administrator_access": ACCOUNT_ADMINISTRATOR in group_names,
        "content_manager_access": CONTENT_MANAGER in group_names,
        "hr_access": "manage_hr" in direct_permissions,
        "staff_access": user.is_staff,
    }


def create_setup_invitation(
    *,
    user: User,
    created_by: User,
    purpose: str,
) -> AccountInvitationResult:
    now = timezone.now()
    AccountInvitation.objects.filter(
        user=user,
        status=AccountInvitationStatus.ACTIVE,
    ).update(
        status=AccountInvitationStatus.CANCELLED,
        cancelled_at=now,
        updated_at=now,
    )
    setup_token = secrets.token_urlsafe(32)
    invitation = AccountInvitation(
        user=user,
        created_by=created_by,
        purpose=purpose,
        token_hash=hash_setup_token(setup_token),
        expires_at=now + INVITATION_LIFETIME,
    )
    invitation.full_clean()
    invitation.save()
    return AccountInvitationResult(
        invitation=invitation,
        setup_token=setup_token,
    )


@transaction.atomic
def create_content_manager_account(
    *,
    created_by: User,
    email: str,
    first_name: str,
    last_name: str,
    phone_number: str,
    grant_hr_access: bool,
    request_path: str,
) -> AccountInvitationResult:
    normalized_email = User.objects.normalize_email(email).lower()
    normalized_phone = phone_number.strip()
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise ValidationError({"email": "This email is already in use."})
    if User.objects.filter(phone_number=normalized_phone).exists():
        raise ValidationError(
            {"phone_number": "This phone number is already in use."}
        )

    user = User.objects.create_user(
        email=normalized_email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        phone_number=normalized_phone,
        password=None,
        is_active=False,
    )
    user.groups.add(Group.objects.get(name=CONTENT_MANAGER))
    if grant_hr_access:
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts",
                codename="manage_hr",
            )
        )

    result = create_setup_invitation(
        user=user,
        created_by=created_by,
        purpose=AccountInvitationPurpose.INITIAL_SETUP,
    )
    record_audit_event(
        domain=AuditDomain.ACCOUNTS,
        action=AuditAction.ACCOUNT_INVITATION_CREATED,
        actor=created_by,
        target_type="user",
        target_id=user.id,
        operation="account_management:create_content_manager",
        request_method="POST",
        request_path=request_path,
        new_state=account_access_state(user),
    )
    return result


@transaction.atomic
def create_reactivation_invitation(
    *,
    user_id,
    created_by: User,
    reason: str,
    request_path: str,
) -> AccountInvitationResult:
    user = User.objects.select_for_update().get(pk=user_id)
    if user.is_superuser:
        raise ValidationError(
            {"account": "Superuser accounts cannot be managed through this API."}
        )
    if user.is_active:
        raise ValidationError({"account": "This account is already active."})

    result = create_setup_invitation(
        user=user,
        created_by=created_by,
        purpose=AccountInvitationPurpose.REACTIVATION,
    )
    record_audit_event(
        domain=AuditDomain.ACCOUNTS,
        action=AuditAction.ACCOUNT_INVITATION_CREATED,
        actor=created_by,
        target_type="user",
        target_id=user.id,
        operation="account_management:activate_account",
        request_method="POST",
        request_path=request_path,
        previous_state=account_access_state(user),
        new_state=account_access_state(user),
        reason=reason,
    )
    return result


def send_account_invitation_email(result: AccountInvitationResult) -> None:
    invitation = result.invitation
    setup_link = build_account_invitation_setup_link(result.setup_token)
    expires_at = timezone.localtime(invitation.expires_at).strftime(
        "%A, %d %B %Y at %H:%M %Z"
    )
    if invitation.purpose == AccountInvitationPurpose.REACTIVATION:
        introduction = "Your Ask For Success account is ready to be reactivated."
    else:
        introduction = "You have been invited to manage content for Ask For Success."

    try:
        message = EmailMessage(
            subject="Set up your Ask For Success account",
            body=(
                f"Hello {invitation.user.first_name},\n\n"
                f"{introduction}\n\n"
                "Set a password and activate your account using this secure link:\n"
                f"{setup_link}\n\n"
                f"This single-use link expires on {expires_at}.\n\n"
                "If you did not expect this invitation, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[invitation.user.email],
        )
        sent_count = message.send(fail_silently=False)
        if sent_count != 1:
            raise RuntimeError("The email service did not confirm delivery.")
    except Exception as error:
        invitation.email_delivery_status = AccountInvitationEmailStatus.FAILED
        invitation.email_sent_at = None
        invitation.email_error = str(error)[:2000]
        invitation.save(
            update_fields=(
                "email_delivery_status",
                "email_sent_at",
                "email_error",
                "updated_at",
            )
        )
        return

    invitation.email_delivery_status = AccountInvitationEmailStatus.SENT
    invitation.email_sent_at = timezone.now()
    invitation.email_error = ""
    invitation.save(
        update_fields=(
            "email_delivery_status",
            "email_sent_at",
            "email_error",
            "updated_at",
        )
    )


@transaction.atomic
def deactivate_account(
    *,
    user_id,
    deactivated_by: User,
    reason: str,
    request_path: str,
) -> User:
    user = User.objects.select_for_update().get(pk=user_id)
    if user.id == deactivated_by.id:
        raise ValidationError({"account": "You cannot deactivate your own account."})
    if user.is_superuser:
        raise ValidationError(
            {"account": "Superuser accounts cannot be deactivated through this API."}
        )
    if not user.is_active:
        raise ValidationError({"account": "This account is already inactive."})

    previous_state = account_access_state(user)
    user.is_active = False
    user.is_staff = False
    user.set_unusable_password()
    user.save(
        update_fields=("is_active", "is_staff", "password", "updated_at")
    )
    user.groups.clear()
    user.user_permissions.clear()
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)

    now = timezone.now()
    AccountInvitation.objects.filter(
        user=user,
        status=AccountInvitationStatus.ACTIVE,
    ).update(
        status=AccountInvitationStatus.CANCELLED,
        cancelled_at=now,
        updated_at=now,
    )
    record_audit_event(
        domain=AuditDomain.ACCOUNTS,
        action=AuditAction.ACCOUNT_DEACTIVATED,
        actor=deactivated_by,
        target_type="user",
        target_id=user.id,
        operation="account_management:deactivate_account",
        request_method="POST",
        request_path=request_path,
        previous_state=previous_state,
        new_state=account_access_state(user),
        reason=reason,
    )
    return user


def accept_account_invitation(*, token: str, password: str) -> User:
    token_hash = hash_setup_token(token)
    expired = False
    with transaction.atomic():
        try:
            invitation = (
                AccountInvitation.objects.select_for_update()
                .select_related("user")
                .get(token_hash=token_hash)
            )
        except AccountInvitation.DoesNotExist as error:
            raise ValidationError(
                {"token": "This invitation is invalid or no longer usable."}
            ) from error

        if invitation.status != AccountInvitationStatus.ACTIVE:
            raise ValidationError(
                {"token": "This invitation is invalid or no longer usable."}
            )
        now = timezone.now()
        if invitation.expires_at <= now:
            invitation.status = AccountInvitationStatus.EXPIRED
            invitation.save(update_fields=("status", "updated_at"))
            expired = True
        else:
            user = User.objects.select_for_update().get(pk=invitation.user_id)
            if user.is_active:
                raise ValidationError(
                    {"token": "This invitation is invalid or no longer usable."}
                )
            password_validation.validate_password(password, user=user)
            user.set_password(password)
            user.is_active = True
            user.save(update_fields=("password", "is_active", "updated_at"))
            invitation.status = AccountInvitationStatus.USED
            invitation.used_at = now
            invitation.save(
                update_fields=("status", "used_at", "updated_at")
            )
            record_audit_event(
                domain=AuditDomain.ACCOUNTS,
                action=AuditAction.ACCOUNT_INVITATION_ACCEPTED,
                actor=user,
                target_type="user",
                target_id=user.id,
                operation="account_management:accept_invitation",
                request_method="POST",
                request_path="/api/v1/account-management/invitations/accept/",
                previous_state={"account_active": False},
                new_state={"account_active": True},
            )

    if expired:
        raise ValidationError({"token": "This invitation has expired."})
    return user
