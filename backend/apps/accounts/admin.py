from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountInvitation, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "is_active",
        "is_staff",
    )
    search_fields = ("email", "first_name", "last_name", "phone_number")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal information",
            {"fields": ("first_name", "last_name", "phone_number")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ("created_at", "last_login")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(AccountInvitation)
class AccountInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "purpose",
        "status",
        "email_delivery_status",
        "expires_at",
        "created_at",
    )
    list_filter = ("purpose", "status", "email_delivery_status")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = (
        "id",
        "user",
        "created_by",
        "purpose",
        "token_hash",
        "status",
        "expires_at",
        "used_at",
        "cancelled_at",
        "email_delivery_status",
        "email_sent_at",
        "email_error",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
