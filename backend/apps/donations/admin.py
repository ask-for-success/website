from django.contrib import admin

from .models import DonationSubmission


@admin.register(DonationSubmission)
class DonationSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "donation_type",
        "acknowledgement_email_status",
        "created_at",
    )
    list_filter = ("donation_type", "acknowledgement_email_status")
    search_fields = ("first_name", "last_name", "email", "phone_number")
    readonly_fields = (
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

