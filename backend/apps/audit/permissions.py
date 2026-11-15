from rest_framework.permissions import BasePermission


class CanViewAuditLog(BasePermission):
    message = "You do not have permission to view the audit log."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("accounts.view_audit_log")
        )
