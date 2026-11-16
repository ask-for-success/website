from django.urls import path

from .management_views import (
    AccountActivateView,
    AccountDeactivateView,
    AccountInvitationAcceptView,
    ManagedAccountDetailView,
    ManagedAccountListCreateView,
)


app_name = "account_management"

urlpatterns = [
    path(
        "accounts/",
        ManagedAccountListCreateView.as_view(),
        name="account_list_create",
    ),
    path(
        "accounts/<uuid:user_id>/",
        ManagedAccountDetailView.as_view(),
        name="account_detail",
    ),
    path(
        "accounts/<uuid:user_id>/deactivate/",
        AccountDeactivateView.as_view(),
        name="deactivate_account",
    ),
    path(
        "accounts/<uuid:user_id>/activate/",
        AccountActivateView.as_view(),
        name="activate_account",
    ),
    path(
        "invitations/accept/",
        AccountInvitationAcceptView.as_view(),
        name="accept_invitation",
    ),
]
