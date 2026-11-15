from django.contrib import admin

from .models import AuditRecord


@admin.register(AuditRecord)
class AuditRecordAdmin(admin.ModelAdmin):
    list_display = ("action", "domain", "actor", "created_at")
    list_filter = ("domain", "action", "created_at")
    search_fields = ("actor__email",)
    readonly_fields = (
        "id",
        "domain",
        "action",
        "actor",
        "application",
        "membership",
        "previous_state",
        "new_state",
        "reason",
        "created_at",
    )

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
