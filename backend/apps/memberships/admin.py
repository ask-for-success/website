from django.contrib import admin

from .models import (
    MemberAssignment,
    Membership,
    MembershipInvitation,
    MembershipOnboarding,
)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "accepted_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    ordering = ("-accepted_at",)


@admin.register(MembershipOnboarding)
class MembershipOnboardingAdmin(admin.ModelAdmin):
    list_display = ("membership", "status", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("membership__user__email",)


@admin.register(MemberAssignment)
class MemberAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "membership",
        "department",
        "position",
        "starts_at",
        "ends_at",
        "assigned_by",
    )
    list_filter = ("department", "position")
    search_fields = (
        "membership__user__email",
        "department__name",
        "position__name",
    )
    ordering = ("-starts_at",)


@admin.register(MembershipInvitation)
class MembershipInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "email_delivery_status",
        "email_sent_at",
        "expires_at",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "email_delivery_status")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "token_hash",
        "created_at",
        "updated_at",
        "used_at",
        "cancelled_at",
        "email_sent_at",
        "email_error",
    )
    ordering = ("-created_at",)
