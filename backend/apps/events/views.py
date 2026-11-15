import csv

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import is_content_manager

from .models import (
    EmailDeliveryStatus,
    Event,
    EventCheckIn,
    EventNotificationType,
    EventParticipantNotification,
    EventQuestionType,
    EventRegistrationSource,
    EventRegistrationStatus,
    EventScanner,
    EventTicket,
    PublicationStatus,
    QrDeliveryStatus,
)
from .operations import (
    EventLifecycleResult,
    check_in_event_registration,
    permanently_cancel_event,
    remove_event_scanner,
    reschedule_event,
    send_event_participant_notifications,
    send_registration_confirmation_email,
)
from .permissions import IsContentManager
from .pagination import EventAdministrationPagination
from .serializers import (
    EventCheckInInputSerializer,
    EventCheckInOutputSerializer,
    EventCancellationSerializer,
    EventLifecycleResultSerializer,
    EventNotificationFilterSerializer,
    EventNotificationPageSerializer,
    EventParticipantNotificationSerializer,
    EventRegistrationCancellationResultSerializer,
    EventRegistrationCancellationSerializer,
    EventRegistrationCreateSerializer,
    EventRegistrationFilterSerializer,
    EventRegistrationPageSerializer,
    EventRegistrationSerializer,
    EventRescheduleSerializer,
    EventScannerAssignmentSerializer,
    EventScannerSerializer,
    EventSerializer,
    EventStatisticsSerializer,
    ManualEventRegistrationCreateSerializer,
    convert_validation_error,
)


EVENT_REGISTRATION_QUERY_PARAMETERS = [
    OpenApiParameter(
        "search",
        str,
        OpenApiParameter.QUERY,
        description="Search registrations by email address.",
    ),
    OpenApiParameter(
        "status",
        str,
        OpenApiParameter.QUERY,
        enum=EventRegistrationStatus.values,
        description="Filter by registration status.",
    ),
    OpenApiParameter(
        "source",
        str,
        OpenApiParameter.QUERY,
        enum=EventRegistrationSource.values,
        description="Filter by public or manual source.",
    ),
    OpenApiParameter(
        "qr_delivery_status",
        str,
        OpenApiParameter.QUERY,
        enum=(*QrDeliveryStatus.values, "not_required"),
        description="Filter by QR delivery state or events without a ticket.",
    ),
    OpenApiParameter(
        "is_checked_in",
        bool,
        OpenApiParameter.QUERY,
        description="Filter by check-in state.",
    ),
    OpenApiParameter(
        "ordering",
        str,
        OpenApiParameter.QUERY,
        description=(
            "Order by registered_at, email, status, source, "
            "confirmation_email_status, qr_delivery_status, or checked_in_at. "
            "Prefix the value with - for descending order."
        ),
    ),
    OpenApiParameter(
        "page",
        int,
        OpenApiParameter.QUERY,
        description="Page number.",
    ),
    OpenApiParameter(
        "page_size",
        int,
        OpenApiParameter.QUERY,
        description="Results per page, up to 200.",
    ),
]


EVENT_NOTIFICATION_QUERY_PARAMETERS = [
    OpenApiParameter(
        "search",
        str,
        OpenApiParameter.QUERY,
        description="Search notification history by participant email.",
    ),
    OpenApiParameter(
        "notification_type",
        str,
        OpenApiParameter.QUERY,
        enum=EventNotificationType.values,
        description="Filter by confirmation, rescheduled, or cancelled.",
    ),
    OpenApiParameter(
        "delivery_status",
        str,
        OpenApiParameter.QUERY,
        enum=EmailDeliveryStatus.values,
        description="Filter by notification delivery state.",
    ),
    OpenApiParameter(
        "ordering",
        str,
        OpenApiParameter.QUERY,
        description=(
            "Order by created_at, sent_at, email, notification_type, or "
            "delivery_status. Prefix the value with - for descending order."
        ),
    ),
    OpenApiParameter("page", int, OpenApiParameter.QUERY),
    OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
]


REGISTRATION_ORDERING_FIELDS = {
    "registered_at": "registered_at",
    "email": "email",
    "status": "status",
    "source": "source",
    "confirmation_email_status": "confirmation_email_status",
    "qr_delivery_status": "ticket__delivery_status",
    "checked_in_at": "ticket__check_in__checked_in_at",
}


NOTIFICATION_ORDERING_FIELDS = {
    "created_at": "created_at",
    "sent_at": "sent_at",
    "email": "registration__email",
    "notification_type": "notification_type",
    "delivery_status": "delivery_status",
}


def event_registration_queryset(event):
    return event.registrations.select_related(
        "ticket__check_in",
    ).prefetch_related(
        "answers__question__options",
    )


def apply_event_registration_filters(queryset, query_params):
    filter_data = (
        query_params.dict() if hasattr(query_params, "dict") else query_params
    )
    serializer = EventRegistrationFilterSerializer(data=filter_data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    search = values.get("search", "").strip()
    if search:
        queryset = queryset.filter(email__icontains=search)
    if "status" in values:
        queryset = queryset.filter(status=values["status"])
    if "source" in values:
        queryset = queryset.filter(source=values["source"])
    if "qr_delivery_status" in values:
        qr_status = values["qr_delivery_status"]
        if qr_status == "not_required":
            queryset = queryset.filter(ticket__isnull=True)
        else:
            queryset = queryset.filter(ticket__delivery_status=qr_status)
    if "is_checked_in" in values:
        queryset = queryset.filter(
            ticket__check_in__isnull=not values["is_checked_in"]
        )
    requested_ordering = values["ordering"]
    descending = requested_ordering.startswith("-")
    field_name = requested_ordering.removeprefix("-")
    database_field = REGISTRATION_ORDERING_FIELDS[field_name]
    if descending:
        database_field = f"-{database_field}"
    return queryset.order_by(database_field, "id")


def apply_event_notification_filters(queryset, query_params):
    filter_data = (
        query_params.dict() if hasattr(query_params, "dict") else query_params
    )
    serializer = EventNotificationFilterSerializer(data=filter_data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    search = values.get("search", "").strip()
    if search:
        queryset = queryset.filter(registration__email__icontains=search)
    if "notification_type" in values:
        queryset = queryset.filter(
            notification_type=values["notification_type"]
        )
    if "delivery_status" in values:
        queryset = queryset.filter(delivery_status=values["delivery_status"])
    requested_ordering = values["ordering"]
    descending = requested_ordering.startswith("-")
    field_name = requested_ordering.removeprefix("-")
    database_field = NOTIFICATION_ORDERING_FIELDS[field_name]
    if descending:
        database_field = f"-{database_field}"
    return queryset.order_by(database_field, "id")


def _registration_ticket(registration):
    try:
        return registration.ticket
    except EventTicket.DoesNotExist:
        return None


def _format_csv_answer(question, value):
    if question.question_type in {
        EventQuestionType.SINGLE_CHOICE,
        EventQuestionType.MULTIPLE_CHOICE,
    }:
        options = {str(option.id): option.label for option in question.options.all()}
        if question.question_type == EventQuestionType.MULTIPLE_CHOICE:
            return " | ".join(options.get(str(item), str(item)) for item in value)
        return options.get(str(value), str(value))
    if question.question_type == EventQuestionType.YES_NO:
        return "Yes" if value else "No"
    return str(value)


def _safe_csv_value(value):
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


class EventListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return (IsContentManager(),)

    @extend_schema(
        tags=["Events"],
        summary="List events",
        parameters=[
            OpenApiParameter(
                name="timing",
                type=str,
                enum=("upcoming", "past"),
                location=OpenApiParameter.QUERY,
                description="Filter events by their end time.",
            )
        ],
        responses={200: EventSerializer(many=True)},
    )
    def get(self, request):
        events = Event.objects.prefetch_related("questions__options")
        if not is_content_manager(request.user):
            events = events.filter(
                publication_status=PublicationStatus.PUBLISHED
            )
        timing = request.query_params.get("timing")
        if timing == "upcoming":
            events = events.filter(ends_at__gte=timezone.now()).order_by(
                "starts_at",
                "title",
            )
        elif timing == "past":
            events = events.filter(ends_at__lt=timezone.now()).order_by(
                "-starts_at",
                "title",
            )
        elif timing:
            raise serializers.ValidationError(
                {"timing": "Use upcoming or past."}
            )
        return Response(EventSerializer(events, many=True).data)

    @extend_schema(
        tags=["Events"],
        summary="Create an event and its registration form",
        request=EventSerializer,
        responses={
            201: EventSerializer,
            400: OpenApiResponse(description="Invalid data."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request):
        serializer = EventSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(
            EventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class EventDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return (permissions.AllowAny(),)
        return (IsContentManager(),)

    def get_event(self, request, event_id):
        events = Event.objects.prefetch_related("questions__options")
        if not is_content_manager(request.user):
            events = events.filter(
                publication_status=PublicationStatus.PUBLISHED
            )
        return get_object_or_404(events, pk=event_id)

    @extend_schema(
        tags=["Events"],
        summary="Get an event",
        responses={200: EventSerializer, 404: OpenApiResponse()},
    )
    def get(self, request, event_id):
        event = self.get_event(request, event_id)
        return Response(EventSerializer(event).data)

    @extend_schema(
        tags=["Events"],
        summary="Update an event",
        request=EventSerializer,
        responses={
            200: EventSerializer,
            400: OpenApiResponse(description="Invalid data."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def patch(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventSerializer(
            event,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        event = serializer.save()
        return Response(EventSerializer(event).data)


class EventRegistrationsView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return (permissions.AllowAny(),)
        return (IsContentManager(),)

    @extend_schema(
        tags=["Events"],
        summary="List registrations for an event",
        description=(
            "Returns a searchable, filterable, ordered, paginated registration "
            "list for the content-manager dashboard."
        ),
        parameters=EVENT_REGISTRATION_QUERY_PARAMETERS,
        responses={200: EventRegistrationPageSerializer},
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        registrations = apply_event_registration_filters(
            event_registration_queryset(event),
            request.query_params,
        )
        paginator = EventAdministrationPagination()
        page = paginator.paginate_queryset(registrations, request, view=self)
        data = EventRegistrationSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    @extend_schema(
        tags=["Events"],
        summary="Register for an event without an account",
        description=(
            "Registers one email address for the event. When QR check-in is "
            "enabled, the ticket is generated automatically. Every successful "
            "registration receives a confirmation email with a secure "
            "cancellation link."
        ),
        request=EventRegistrationCreateSerializer,
        responses={
            201: EventRegistrationSerializer,
            400: OpenApiResponse(description="Invalid registration."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventRegistrationCreateSerializer(
            data=request.data,
            context={"event": event},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        send_registration_confirmation_email(result)
        result.registration.refresh_from_db()
        return Response(
            EventRegistrationSerializer(result.registration).data,
            status=status.HTTP_201_CREATED,
        )


class EventStatisticsView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Get event registration and attendance statistics",
        responses={
            200: EventStatisticsSerializer,
            403: OpenApiResponse(description="Content manager access required."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        counts = event.registrations.aggregate(
            registered_count=Count(
                "id",
                filter=Q(status=EventRegistrationStatus.REGISTERED),
            ),
            cancelled_count=Count(
                "id",
                filter=Q(status=EventRegistrationStatus.CANCELLED),
            ),
        )
        checked_in_count = EventCheckIn.objects.filter(
            ticket__registration__event=event
        ).count()
        remaining_seats = None
        if event.capacity is not None:
            remaining_seats = max(
                event.capacity - counts["registered_count"],
                0,
            )
        data = {
            "event_id": event.id,
            "capacity": event.capacity,
            "registered_count": counts["registered_count"],
            "cancelled_count": counts["cancelled_count"],
            "checked_in_count": checked_in_count,
            "remaining_seats": remaining_seats,
        }
        return Response(EventStatisticsSerializer(data).data)


class EventRegistrationExportView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Export event participants and form answers as CSV",
        description=(
            "Applies the registration search, filters, and ordering but ignores "
            "page and page_size so every matching row is exported."
        ),
        parameters=EVENT_REGISTRATION_QUERY_PARAMETERS,
        responses={
            (200, "text/csv"): OpenApiTypes.BINARY,
            403: OpenApiResponse(description="Content manager access required."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def get(self, request, event_id):
        event = get_object_or_404(
            Event.objects.prefetch_related("questions__options"),
            pk=event_id,
        )
        registrations = apply_event_registration_filters(
            event_registration_queryset(event),
            request.query_params,
        )
        questions = list(event.questions.prefetch_related("options"))
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="event-{event.id}-participants.csv"'
        )
        response.write("\ufeff")
        writer = csv.writer(response, lineterminator="\n")
        fixed_headers = [
            "registration_id",
            "email",
            "status",
            "source",
            "registered_at",
            "cancelled_at",
            "cancellation_source",
            "confirmation_email_status",
            "qr_delivery_status",
            "is_checked_in",
            "checked_in_at",
        ]
        answer_headers = [
            f"answer:{question.display_order}:{question.label}"
            for question in questions
        ]
        writer.writerow(fixed_headers + answer_headers)

        for registration in registrations:
            ticket = _registration_ticket(registration)
            check_in = (
                ticket.check_in
                if ticket is not None and hasattr(ticket, "check_in")
                else None
            )
            answers = {
                answer.question_id: answer.value
                for answer in registration.answers.all()
            }
            row = [
                registration.id,
                registration.email,
                registration.status,
                registration.source,
                registration.registered_at.isoformat(),
                registration.cancelled_at.isoformat()
                if registration.cancelled_at
                else "",
                registration.cancellation_source,
                registration.confirmation_email_status,
                ticket.delivery_status if ticket else "not_required",
                "true" if check_in else "false",
                check_in.checked_in_at.isoformat() if check_in else "",
            ]
            for question in questions:
                value = answers.get(question.id)
                row.append(
                    _format_csv_answer(question, value)
                    if value is not None
                    else ""
                )
            writer.writerow([_safe_csv_value(value) for value in row])
        return response


class EventNotificationHistoryView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="List event participant notification history",
        description=(
            "Returns confirmation, reschedule, and cancellation delivery "
            "attempts with their current delivery outcome."
        ),
        parameters=EVENT_NOTIFICATION_QUERY_PARAMETERS,
        responses={
            200: EventNotificationPageSerializer,
            403: OpenApiResponse(description="Content manager access required."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        notifications = apply_event_notification_filters(
            EventParticipantNotification.objects.filter(event=event).select_related(
                "registration"
            ),
            request.query_params,
        )
        paginator = EventAdministrationPagination()
        page = paginator.paginate_queryset(notifications, request, view=self)
        data = EventParticipantNotificationSerializer(page, many=True).data
        return paginator.get_paginated_response(data)


class ManualEventRegistrationView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Add an event participant manually",
        description=(
            "Applies the same required answers, duplicate rule, registration "
            "window, and capacity limit as public registration. The participant "
            "receives the normal confirmation email and cancellation link."
        ),
        request=ManualEventRegistrationCreateSerializer,
        responses={
            201: EventRegistrationSerializer,
            400: OpenApiResponse(description="Invalid registration."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = ManualEventRegistrationCreateSerializer(
            data=request.data,
            context={"event": event},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        send_registration_confirmation_email(result)
        result.registration.refresh_from_db()
        return Response(
            EventRegistrationSerializer(result.registration).data,
            status=status.HTTP_201_CREATED,
        )


class EventRegistrationCancellationView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Events"],
        summary="Cancel an event registration using its secure link",
        description=(
            "Cancels one registration and releases its seat. Self-service "
            "cancellation closes exactly 24 hours before the event starts."
        ),
        request=EventRegistrationCancellationSerializer,
        responses={
            200: EventRegistrationCancellationResultSerializer,
            400: OpenApiResponse(
                description="Invalid, expired, late, or already-used link."
            ),
        },
    )
    def post(self, request):
        serializer = EventRegistrationCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.save()
        response_data = {
            "registration_id": registration.id,
            "event_id": registration.event_id,
            "status": registration.status,
            "cancelled_at": registration.cancelled_at,
        }
        return Response(
            EventRegistrationCancellationResultSerializer(response_data).data
        )


class EventRescheduleView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Reschedule an event",
        description=(
            "Changes the event schedule and shifts its registration closing "
            "time by the same interval. Participant notification defaults to "
            "true. Existing registrations and QR codes remain valid."
        ),
        request=EventRescheduleSerializer,
        responses={
            200: EventLifecycleResultSerializer,
            400: OpenApiResponse(description="Invalid reschedule operation."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        notify_participants = values.pop("notify_participants")
        try:
            event, registrations = reschedule_event(
                event=event,
                updated_by=request.user,
                **values,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error

        if notify_participants:
            result = send_event_participant_notifications(
                event=event,
                registrations=registrations,
                notification_type=EventNotificationType.RESCHEDULED,
            )
        else:
            result = EventLifecycleResult(
                event=event,
                notification_type=EventNotificationType.RESCHEDULED,
                notification_count=0,
                sent_count=0,
                failed_count=0,
            )
        return Response(EventLifecycleResultSerializer(result).data)


class EventCancellationView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Permanently cancel an event",
        description=(
            "Permanently cancels the event and all active registrations. "
            "Tickets and cancellation links become invalid. Participant "
            "notification defaults to true."
        ),
        request=EventCancellationSerializer,
        responses={
            200: EventLifecycleResultSerializer,
            400: OpenApiResponse(description="Invalid cancellation operation."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event, registrations = permanently_cancel_event(
                event=event,
                cancelled_by=request.user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error

        if serializer.validated_data["notify_participants"]:
            result = send_event_participant_notifications(
                event=event,
                registrations=registrations,
                notification_type=EventNotificationType.CANCELLED,
            )
        else:
            result = EventLifecycleResult(
                event=event,
                notification_type=EventNotificationType.CANCELLED,
                notification_count=0,
                sent_count=0,
                failed_count=0,
            )
        return Response(EventLifecycleResultSerializer(result).data)


class EventScannersView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="List scanners for an event",
        responses={200: EventScannerSerializer(many=True)},
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        scanners = event.scanners.select_related("membership", "assigned_by")
        return Response(EventScannerSerializer(scanners, many=True).data)

    @extend_schema(
        tags=["Events"],
        summary="Assign an active member as an event scanner",
        request=EventScannerAssignmentSerializer,
        responses={
            201: EventScannerSerializer,
            400: OpenApiResponse(description="Invalid membership."),
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventScannerAssignmentSerializer(
            data=request.data,
            context={"request": request, "event": event},
        )
        serializer.is_valid(raise_exception=True)
        scanner = serializer.save()
        return Response(
            EventScannerSerializer(scanner).data,
            status=status.HTTP_201_CREATED,
        )


class EventScannerRemovalView(APIView):
    permission_classes = (IsContentManager,)

    @extend_schema(
        tags=["Events"],
        summary="Remove a member's event scanner access",
        responses={204: None, 404: OpenApiResponse()},
    )
    def delete(self, request, event_id, membership_id):
        scanner = get_object_or_404(
            EventScanner,
            event_id=event_id,
            membership_id=membership_id,
        )
        remove_event_scanner(scanner=scanner, removed_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventCheckInView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        tags=["Events"],
        summary="Check in an event ticket",
        request=EventCheckInInputSerializer,
        responses={
            200: EventCheckInOutputSerializer,
            400: OpenApiResponse(description="Invalid QR code."),
            403: OpenApiResponse(description="Scanner access required."),
        },
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        serializer = EventCheckInInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = check_in_event_registration(
                event=event,
                user=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        registration = result.check_in.ticket.registration
        response_data = {
            "status": result.status,
            "registration_id": registration.id,
            "email": registration.email,
            "checked_in_at": result.check_in.checked_in_at,
        }
        return Response(EventCheckInOutputSerializer(response_data).data)
