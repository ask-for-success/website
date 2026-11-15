from django.urls import path

from .views import (
    DonationSubmissionDetailView,
    DonationSubmissionListView,
    PublicDonationSubmissionView,
)


app_name = "donations"

urlpatterns = [
    path(
        "submissions/",
        PublicDonationSubmissionView.as_view(),
        name="submission_create",
    ),
    path(
        "management/submissions/",
        DonationSubmissionListView.as_view(),
        name="submission_list",
    ),
    path(
        "management/submissions/<uuid:submission_id>/",
        DonationSubmissionDetailView.as_view(),
        name="submission_detail",
    ),
]

