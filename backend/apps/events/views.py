from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import is_content_manager

from .models import Event, EventScanner, PublicationStatus
from .operations import (
    check_in_event_registration,
    remove_event_scanner,
    send_qr_code_email,
)
from .permissions import IsContentManager
from .serializers import (
    EventCheckInInputSerializer,
    EventCheckInOutputSerializer,
    EventRegistrationCreateSerializer,
    EventRegistrationSerializer,
    EventScannerAssignmentSerializer,
    EventScannerSerializer,
    EventSerializer,
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
            "enabled, the ticket is generated and emailed automatically."
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
        send_qr_code_email(result)
        result.registration.refresh_from_db()
        return Response(
            EventRegistrationSerializer(result.registration).data,
            status=status.HTTP_201_CREATED,
        )


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
