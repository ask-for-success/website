from django.contrib import admin

from .models import Department, Position


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "is_active", "updated_at")
    list_filter = ("department", "is_active")
    search_fields = ("name", "department__name")
    ordering = ("department__name", "name")
