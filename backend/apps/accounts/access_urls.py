from django.urls import path

from .access_views import (
    AccessOptionsView,
    CurrentAccessView,
    UserAccessAssignmentView,
)


app_name = "access_control"

urlpatterns = [
    path("me/", CurrentAccessView.as_view(), name="current_access"),
    path("options/", AccessOptionsView.as_view(), name="access_options"),
    path(
        "users/<uuid:user_id>/",
        UserAccessAssignmentView.as_view(),
        name="user_access_assignment",
    ),
]
