from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


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
