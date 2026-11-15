from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.memberships.models import Membership

from .models import (
    Event,
    EventQuestion,
    EventQuestionOption,
    EventQuestionType,
    EventRegistration,
    EventScanner,
    EventTicket,
    QrDeliveryStatus,
)
from .operations import assign_event_scanner, create_event_registration


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class EventQuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventQuestionOption
        fields = ("id", "label", "display_order")
        read_only_fields = ("id",)


class EventQuestionSerializer(serializers.ModelSerializer):
    options = EventQuestionOptionSerializer(many=True, required=False)

    class Meta:
        model = EventQuestion
        fields = (
            "id",
            "label",
            "question_type",
            "is_required",
            "display_order",
            "options",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        options = data.get("options", [])
        question_type = data.get("question_type")
        supports_options = question_type in {
            EventQuestionType.SINGLE_CHOICE,
            EventQuestionType.MULTIPLE_CHOICE,
        }
        if supports_options and len(options) < 2:
            raise serializers.ValidationError(
                {"options": "A choice question requires at least two options."}
            )
        if not supports_options and options:
            raise serializers.ValidationError(
                {"options": "This question type does not accept options."}
            )
        display_orders = [option["display_order"] for option in options]
        if len(display_orders) != len(set(display_orders)):
            raise serializers.ValidationError(
                {"options": "Option display orders must be unique."}
            )
        return data


class EventSerializer(serializers.ModelSerializer):
    questions = EventQuestionSerializer(many=True, required=False)

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "summary",
            "description",
            "location",
            "starts_at",
            "ends_at",
            "registration_opens_at",
            "registration_closes_at",
            "publication_status",
            "requires_qr_code",
            "questions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_questions(self, questions):
        display_orders = [question["display_order"] for question in questions]
        if len(display_orders) != len(set(display_orders)):
            raise serializers.ValidationError(
                "Question display orders must be unique."
            )
        return questions

    def validate(self, data):
        instance = self.instance
        date_values = {
            "starts_at": data.get(
                "starts_at",
                instance.starts_at if instance else None,
            ),
            "ends_at": data.get(
                "ends_at",
                instance.ends_at if instance else None,
            ),
            "registration_opens_at": data.get(
                "registration_opens_at",
                instance.registration_opens_at if instance else None,
            ),
            "registration_closes_at": data.get(
                "registration_closes_at",
                instance.registration_closes_at if instance else None,
            ),
        }
        temporary_event = Event(
            title=data.get("title", instance.title if instance else ""),
            description=data.get(
                "description",
                instance.description if instance else "",
            ),
            location=data.get(
                "location",
                instance.location if instance else "",
            ),
            **date_values,
        )
        try:
            temporary_event.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        return data

    @staticmethod
    def _create_questions(event, questions):
        for question_data in questions:
            options = question_data.pop("options", [])
            question = EventQuestion.objects.create(
                event=event,
                **question_data,
            )
            for option_data in options:
                EventQuestionOption.objects.create(
                    question=question,
                    **option_data,
                )

    @transaction.atomic
    def create(self, validated_data):
        questions = validated_data.pop("questions", [])
        event = Event(
            created_by=self.context["request"].user,
            **validated_data,
        )
        event.full_clean()
        event.save()
        self._create_questions(event, questions)
        return event

    @transaction.atomic
    def update(self, instance, validated_data):
        questions = validated_data.pop("questions", None)
        has_registrations = instance.registrations.exists()
        if has_registrations:
            errors = {}
            if questions is not None:
                errors["questions"] = (
                    "The form cannot be replaced after a registration exists."
                )
            if (
                "requires_qr_code" in validated_data
                and validated_data["requires_qr_code"]
                != instance.requires_qr_code
            ):
                errors["requires_qr_code"] = (
                    "The QR-code requirement cannot change after a registration exists."
                )
            if errors:
                raise serializers.ValidationError(errors)
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.full_clean()
        instance.save()
        if questions is not None:
            instance.questions.all().delete()
            self._create_questions(instance, questions)
        return instance


class EventAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    value = serializers.JSONField()


class EventRegistrationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    answers = EventAnswerInputSerializer(many=True, required=False)

    def create(self, validated_data):
        try:
            return create_event_registration(
                event=self.context["event"],
                answers=validated_data.pop("answers", []),
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class EventAnswerOutputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(source="question.id")
    question = serializers.CharField(source="question.label")
    value = serializers.JSONField()


class EventRegistrationSerializer(serializers.ModelSerializer):
    answers = EventAnswerOutputSerializer(many=True, read_only=True)
    requires_qr_code = serializers.BooleanField(
        source="event.requires_qr_code",
        read_only=True,
    )
    qr_delivery_status = serializers.SerializerMethodField()
    is_checked_in = serializers.SerializerMethodField()
    checked_in_at = serializers.SerializerMethodField()

    class Meta:
        model = EventRegistration
        fields = (
            "id",
            "email",
            "status",
            "registered_at",
            "requires_qr_code",
            "qr_delivery_status",
            "is_checked_in",
            "checked_in_at",
            "answers",
        )

    @staticmethod
    def _get_ticket(instance):
        try:
            return instance.ticket
        except EventTicket.DoesNotExist:
            return None

    @extend_schema_field(
        serializers.ChoiceField(
            choices=QrDeliveryStatus.choices,
            allow_null=True,
        )
    )
    def get_qr_delivery_status(self, instance):
        ticket = self._get_ticket(instance)
        return ticket.delivery_status if ticket else None

    @extend_schema_field(serializers.BooleanField())
    def get_is_checked_in(self, instance):
        ticket = self._get_ticket(instance)
        return bool(ticket and hasattr(ticket, "check_in"))

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_checked_in_at(self, instance):
        ticket = self._get_ticket(instance)
        if ticket and hasattr(ticket, "check_in"):
            return ticket.check_in.checked_in_at
        return None


class EventScannerAssignmentSerializer(serializers.Serializer):
    membership_id = serializers.PrimaryKeyRelatedField(
        queryset=Membership.objects.all(),
        source="membership",
    )

    def create(self, validated_data):
        try:
            return assign_event_scanner(
                event=self.context["event"],
                assigned_by=self.context["request"].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error


class EventScannerSerializer(serializers.ModelSerializer):
    membership_id = serializers.UUIDField(source="membership.id")
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    assigned_by = serializers.EmailField(source="assigned_by.email")

    class Meta:
        model = EventScanner
        fields = (
            "id",
            "membership_id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "assigned_by",
            "assigned_at",
        )

    @extend_schema_field(serializers.EmailField())
    def get_email(self, instance):
        return instance.membership.user.email

    @extend_schema_field(serializers.CharField())
    def get_first_name(self, instance):
        return instance.membership.user.first_name

    @extend_schema_field(serializers.CharField())
    def get_last_name(self, instance):
        return instance.membership.user.last_name


class EventCheckInInputSerializer(serializers.Serializer):
    qr_code = serializers.CharField(trim_whitespace=False)


class EventCheckInOutputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=("checked_in", "already_checked_in")
    )
    registration_id = serializers.UUIDField()
    email = serializers.EmailField()
    checked_in_at = serializers.DateTimeField()
