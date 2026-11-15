from django.urls import path

from .views import (
    AuditActorListView,
    AuditActorRecordListView,
    AuditRecordDetailView,
    AuditRecordListView,
)


app_name = "audit"

urlpatterns = [
    path("actors/", AuditActorListView.as_view(), name="actor_list"),
    path(
        "actors/<uuid:actor_id>/records/",
        AuditActorRecordListView.as_view(),
        name="actor_record_list",
    ),
    path("records/", AuditRecordListView.as_view(), name="record_list"),
    path(
        "records/<uuid:record_id>/",
        AuditRecordDetailView.as_view(),
        name="record_detail",
    ),
]
