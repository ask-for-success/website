from django.urls import path

from .views import (
    EventCancellationView,
    EventCheckInView,
    EventDetailView,
    EventListCreateView,
    EventNotificationHistoryView,
    EventRegistrationExportView,
    EventRegistrationsView,
    EventRegistrationCancellationView,
    EventRescheduleView,
    EventScannerRemovalView,
    EventScannersView,
    EventStatisticsView,
    ManualEventRegistrationView,
)


app_name = "events"

urlpatterns = [
    path("", EventListCreateView.as_view(), name="list_create"),
    path("<uuid:event_id>/", EventDetailView.as_view(), name="detail"),
    path(
        "<uuid:event_id>/registrations/",
        EventRegistrationsView.as_view(),
        name="registrations",
    ),
    path(
        "<uuid:event_id>/registrations/manual/",
        ManualEventRegistrationView.as_view(),
        name="manual_registration",
    ),
    path(
        "<uuid:event_id>/registrations/export/",
        EventRegistrationExportView.as_view(),
        name="registration_export",
    ),
    path(
        "<uuid:event_id>/statistics/",
        EventStatisticsView.as_view(),
        name="statistics",
    ),
    path(
        "<uuid:event_id>/notifications/",
        EventNotificationHistoryView.as_view(),
        name="notification_history",
    ),
    path(
        "registrations/cancel/",
        EventRegistrationCancellationView.as_view(),
        name="cancel_registration",
    ),
    path(
        "<uuid:event_id>/reschedule/",
        EventRescheduleView.as_view(),
        name="reschedule",
    ),
    path(
        "<uuid:event_id>/cancel/",
        EventCancellationView.as_view(),
        name="cancel",
    ),
    path(
        "<uuid:event_id>/scanners/",
        EventScannersView.as_view(),
        name="scanners",
    ),
    path(
        "<uuid:event_id>/scanners/<uuid:membership_id>/",
        EventScannerRemovalView.as_view(),
        name="remove_scanner",
    ),
    path(
        "<uuid:event_id>/check-ins/",
        EventCheckInView.as_view(),
        name="check_in",
    ),
]
