from django.contrib import admin

from .models import (
    Event,
    EventAnswer,
    EventCheckIn,
    EventParticipantNotification,
    EventQuestion,
    EventQuestionOption,
    EventRegistration,
    EventScanner,
    EventTicket,
)


class EventQuestionOptionInline(admin.TabularInline):
    model = EventQuestionOption
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "starts_at",
        "publication_status",
        "capacity",
        "requires_qr_code",
        "created_by",
    )
    list_filter = ("publication_status", "requires_qr_code")
    search_fields = ("title", "description", "location")
    ordering = ("-starts_at",)


@admin.register(EventQuestion)
class EventQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "event",
        "question_type",
        "is_required",
        "display_order",
    )
    list_filter = ("question_type", "is_required")
    inlines = (EventQuestionOptionInline,)


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "event",
        "status",
        "source",
        "confirmation_email_status",
        "registered_at",
    )
    list_filter = ("event", "status", "source", "confirmation_email_status")
    search_fields = ("email", "event__title")
    ordering = ("-registered_at",)


admin.site.register(EventAnswer)
admin.site.register(EventTicket)
admin.site.register(EventParticipantNotification)
admin.site.register(EventScanner)
admin.site.register(EventCheckIn)
