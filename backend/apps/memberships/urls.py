from django.urls import path

from .views import (
    ExistingAccountAdmissionView,
    MembershipDepartureView,
    MembershipDetailView,
    MembershipInvitationAcceptView,
    MembershipInvitationCreateView,
    MembershipIdentityView,
    MembershipListView,
    MyMembershipSummaryView,
    MyMembershipOnboardingView,
    MembershipOnboardingView,
    MembershipTransferView,
)


app_name = "memberships"

urlpatterns = [
    path("", MembershipListView.as_view(), name="list"),
    path("me/", MyMembershipSummaryView.as_view(), name="my_summary"),
    path(
        "me/onboarding/",
        MyMembershipOnboardingView.as_view(),
        name="my_onboarding",
    ),
    path(
        "admissions/",
        ExistingAccountAdmissionView.as_view(),
        name="admit_existing_account",
    ),
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
    path(
        "<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="detail",
    ),
    path(
        "<uuid:membership_id>/identity/",
        MembershipIdentityView.as_view(),
        name="identity",
    ),
    path(
        "<uuid:membership_id>/transfers/",
        MembershipTransferView.as_view(),
        name="transfer",
    ),
    path(
        "<uuid:membership_id>/onboarding/",
        MembershipOnboardingView.as_view(),
        name="onboarding",
    ),
    path(
        "<uuid:membership_id>/departures/",
        MembershipDepartureView.as_view(),
        name="departure",
    ),
]
