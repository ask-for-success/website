from rest_framework.permissions import BasePermission


class CanManageAccessAssignments(BasePermission):
    message = "You do not have permission to manage access assignments."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("accounts.manage_access_assignments")
        )


def is_content_manager(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.has_perm("accounts.manage_content"))
    )


class IsContentManager(BasePermission):
    message = "This operation is restricted to content managers."

    def has_permission(self, request, view) -> bool:
        return is_content_manager(request.user)


def is_hr_manager(user) -> bool:
    return bool(
        is_content_manager(user)
        and (user.is_superuser or user.has_perm("accounts.manage_hr"))
    )


class CanManageHr(BasePermission):
    message = "This operation requires content-manager access and HR permission."

    def has_permission(self, request, view) -> bool:
        return is_hr_manager(request.user)


def can_view_sensitive_identity(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or is_hr_manager(user)
            or user.has_perm("accounts.manage_accounts")
        )
    )


class CanViewSensitiveIdentity(BasePermission):
    message = "HR or account-administrator access is required."

    def has_permission(self, request, view) -> bool:
        return can_view_sensitive_identity(request.user)
