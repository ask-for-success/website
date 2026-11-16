from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("memberships", "0002_memberidentity"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipinvitation",
            name="email_delivery_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="membershipinvitation",
            name="email_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="membershipinvitation",
            name="email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
