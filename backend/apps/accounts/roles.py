from dataclasses import dataclass


@dataclass(frozen=True)
class RoleDefinition:
    key: str
    description: str
    permissions: tuple[str, ...]


@dataclass(frozen=True)
class AdditionalPermissionDefinition:
    key: str
    description: str
    requires_role: str


ACCOUNT_ADMINISTRATOR = "account_administrator"
CONTENT_MANAGER = "content_manager"

SYSTEM_ROLES = (
    RoleDefinition(
        key=ACCOUNT_ADMINISTRATOR,
        description="Manages user accounts and global role assignments.",
        permissions=(
            "accounts.manage_accounts",
            "accounts.manage_access_assignments",
            "accounts.view_audit_log",
        ),
    ),
    RoleDefinition(
        key=CONTENT_MANAGER,
        description=(
            "Manages website content, events, forms, and event-specific "
            "scanner assignments."
        ),
        permissions=("accounts.manage_content",),
    ),
)

ADDITIONAL_PERMISSIONS = (
    AdditionalPermissionDefinition(
        key="accounts.manage_hr",
        description=(
            "Allows a content manager to manage recruitment and official "
            "membership records."
        ),
        requires_role=CONTENT_MANAGER,
    ),
)

SYSTEM_ROLE_KEYS = tuple(role.key for role in SYSTEM_ROLES)
SYSTEM_ROLE_BY_KEY = {role.key: role for role in SYSTEM_ROLES}
ADDITIONAL_PERMISSION_KEYS = tuple(
    permission.key for permission in ADDITIONAL_PERMISSIONS
)
ADDITIONAL_PERMISSION_BY_KEY = {
    permission.key: permission for permission in ADDITIONAL_PERMISSIONS
}
ADDITIONAL_PERMISSION_CODENAMES = tuple(
    permission.key.split(".", 1)[1] for permission in ADDITIONAL_PERMISSIONS
)
SYSTEM_PERMISSION_CODES = tuple(
    dict.fromkeys(
        permission
        for role in SYSTEM_ROLES
        for permission in role.permissions
    )
) + ADDITIONAL_PERMISSION_KEYS


def get_user_role_keys(user) -> list[str]:
    return list(
        user.groups.filter(name__in=SYSTEM_ROLE_KEYS)
        .order_by("name")
        .values_list("name", flat=True)
    )


def get_user_permission_codes(user) -> list[str]:
    return sorted(
        permission
        for permission in SYSTEM_PERMISSION_CODES
        if user.has_perm(permission)
    )


def get_user_direct_permission_codes(user) -> list[str]:
    codenames = user.user_permissions.filter(
        content_type__app_label="accounts",
        codename__in=ADDITIONAL_PERMISSION_CODENAMES,
    ).values_list("codename", flat=True)
    return sorted(f"accounts.{codename}" for codename in codenames)
