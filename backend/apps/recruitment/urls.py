from django.urls import path

from .views import (
    ApplicationCvView,
    CandidateApplicationListView,
    RecruitmentApplicationCreateView,
    RecruitmentApplicationDetailView,
    RecruitmentApplicationListView,
    RecruitmentApplicationStatusView,
    RecruitmentFormDetailView,
    RecruitmentFormListCreateView,
    RecruitmentOpportunityDetailView,
    RecruitmentOpportunityListCreateView,
)


app_name = "recruitment"

urlpatterns = [
    path("forms/", RecruitmentFormListCreateView.as_view(), name="form_list_create"),
    path(
        "forms/<uuid:form_id>/",
        RecruitmentFormDetailView.as_view(),
        name="form_detail",
    ),
    path(
        "opportunities/",
        RecruitmentOpportunityListCreateView.as_view(),
        name="opportunity_list_create",
    ),
    path(
        "opportunities/<slug:opportunity_slug>/",
        RecruitmentOpportunityDetailView.as_view(),
        name="opportunity_detail",
    ),
    path(
        "opportunities/<uuid:opportunity_id>/applications/",
        RecruitmentApplicationCreateView.as_view(),
        name="application_create",
    ),
    path(
        "applications/me/",
        CandidateApplicationListView.as_view(),
        name="candidate_application_list",
    ),
    path(
        "applications/",
        RecruitmentApplicationListView.as_view(),
        name="application_list",
    ),
    path(
        "applications/<uuid:application_id>/",
        RecruitmentApplicationDetailView.as_view(),
        name="application_detail",
    ),
    path(
        "applications/<uuid:application_id>/status/",
        RecruitmentApplicationStatusView.as_view(),
        name="application_status",
    ),
    path(
        "applications/<uuid:application_id>/cv/",
        ApplicationCvView.as_view(),
        name="application_cv",
    ),
]
