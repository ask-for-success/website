from django.urls import path

from .views import DepartmentDetailView, DepartmentListView


app_name = "organization"

urlpatterns = [
    path("departments/", DepartmentListView.as_view(), name="department_list"),
    path(
        "departments/<uuid:department_id>/",
        DepartmentDetailView.as_view(),
        name="department_detail",
    ),
]
