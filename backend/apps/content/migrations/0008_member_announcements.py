import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0007_make_gallery_video_thumbnail_optional"),
        ("events", "0004_event_confirmation_notifications"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MemberAnnouncement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("published_at", models.DateTimeField(default=timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "article",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="member_announcements",
                        to="content.newsarticle",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_member_announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "event",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="member_announcements",
                        to="events.event",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_member_announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "member_announcements",
                "ordering": ("-published_at", "-created_at"),
                "indexes": (
                    models.Index(
                        fields=("is_active", "published_at", "expires_at"),
                        name="member_announce_visible_idx",
                    ),
                ),
                "constraints": (
                    models.CheckConstraint(
                        condition=(
                            Q(("event__isnull", True))
                            | Q(("article__isnull", True))
                        ),
                        name="member_announce_one_ref",
                    ),
                ),
            },
        ),
    ]
