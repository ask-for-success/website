from rest_framework.permissions import BasePermission


class CanManageAccessAssignments(BasePermission):
    message = "You do not have permission to manage access assignments."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("accounts.manage_access_assignments")
        )
