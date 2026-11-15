from rest_framework.permissions import BasePermission


class IsContentManager(BasePermission):
    message = "This operation is restricted to content managers."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name="content_manager").exists()
            )
        )
