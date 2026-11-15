from django.urls import path

from .views import (
    MembershipInvitationAcceptView,
    MembershipInvitationCreateView,
)


app_name = "memberships"

urlpatterns = [
    path(
        "invitations/",
        MembershipInvitationCreateView.as_view(),
        name="create_invitation",
    ),
    path(
        "invitations/accept/",
        MembershipInvitationAcceptView.as_view(),
        name="accept_invitation",
    ),
]
