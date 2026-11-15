from django.db import migrations, models


def backfill_confirmation_notifications(apps, schema_editor):
    EventRegistration = apps.get_model("events", "EventRegistration")
    EventParticipantNotification = apps.get_model(
        "events",
        "EventParticipantNotification",
    )
    registrations = EventRegistration.objects.exclude(
        confirmation_email_status="pending"
    ).iterator()
    for registration in registrations:
        if EventParticipantNotification.objects.filter(
            registration_id=registration.id,
            notification_type="confirmation",
        ).exists():
            continue
        notification = EventParticipantNotification.objects.create(
            event_id=registration.event_id,
            registration_id=registration.id,
            notification_type="confirmation",
            delivery_status=registration.confirmation_email_status,
            sent_at=registration.confirmation_email_sent_at,
            delivery_error=registration.confirmation_email_error,
        )
        EventParticipantNotification.objects.filter(pk=notification.pk).update(
            created_at=registration.registered_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0003_event_lifecycle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventparticipantnotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("confirmation", "Confirmation"),
                    ("rescheduled", "Rescheduled"),
                    ("cancelled", "Cancelled"),
                ],
                max_length=16,
            ),
        ),
        migrations.RunPython(
            backfill_confirmation_notifications,
            migrations.RunPython.noop,
        ),
    ]
