from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import DonationSubmission


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class DonationSubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationSubmission
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "donation_type",
            "details",
        )

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name is required.")
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Last name is required.")
        return value

    def validate_email(self, value):
        return value.strip().lower()

    def validate_phone_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        return value

    def validate_details(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Donation details are required.")
        return value

    def create(self, validated_data):
        instance = DonationSubmission(**validated_data)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        instance.save()
        return instance


class DonationSubmissionReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationSubmission
        fields = (
            "id",
            "donation_type",
            "acknowledgement_email_status",
            "created_at",
        )
        read_only_fields = fields


class DonationSubmissionManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationSubmission
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "donation_type",
            "details",
            "acknowledgement_email_status",
            "acknowledgement_email_sent_at",
            "acknowledgement_email_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

