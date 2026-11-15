from django.urls import path

from .views import AuditRecordDetailView, AuditRecordListView


app_name = "audit"

urlpatterns = [
    path("records/", AuditRecordListView.as_view(), name="record_list"),
    path(
        "records/<uuid:record_id>/",
        AuditRecordDetailView.as_view(),
        name="record_detail",
    ),
]
