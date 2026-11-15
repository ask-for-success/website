from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import is_content_manager

from .models import (
    Event,
    EventNotificationType,
    EventScanner,
    PublicationStatus,
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
from .serializers import (
    EventCheckInInputSerializer,
    EventCheckInOutputSerializer,
    EventCancellationSerializer,
    EventLifecycleResultSerializer,
    EventRegistrationCancellationResultSerializer,
    EventRegistrationCancellationSerializer,
    EventRegistrationCreateSerializer,
    EventRegistrationSerializer,
    EventRescheduleSerializer,
    EventScannerAssignmentSerializer,
    EventScannerSerializer,
    EventSerializer,
    ManualEventRegistrationCreateSerializer,
    convert_validation_error,
)


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
        responses={200: EventRegistrationSerializer(many=True)},
    )
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        registrations = event.registrations.prefetch_related(
            "answers__question",
        ).select_related("ticket__check_in")
        return Response(
            EventRegistrationSerializer(registrations, many=True).data
        )

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
