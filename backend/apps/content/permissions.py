from rest_framework.permissions import BasePermission

from apps.memberships.models import Membership, MembershipStatus


class IsActiveMember(BasePermission):
    message = "An active membership is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and Membership.objects.filter(
                user=request.user,
                status=MembershipStatus.ACTIVE,
            ).exists()
        )
