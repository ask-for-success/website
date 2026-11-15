from django.urls import path

from .views import (
    EventCancellationView,
    EventCheckInView,
    EventDetailView,
    EventListCreateView,
    EventRegistrationsView,
    EventRegistrationCancellationView,
    EventRescheduleView,
    EventScannerRemovalView,
    EventScannersView,
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
