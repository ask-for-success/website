from django.db import migrations


PAGE_SETTINGS = (
    (
        "news",
        "Latest articles",
        "Recaps, announcements and stories.",
    ),
    (
        "gallery",
        "Moments that tell our story.",
        (
            "Summits, workshops and outreach days across Morocco, captured by "
            "our volunteers and the students themselves."
        ),
    ),
)

CATEGORIES = {
    "news": (
        ("Events", "events"),
        ("Student stories", "student-stories"),
        ("Partners", "partners"),
        ("Announcements", "announcements"),
    ),
    "gallery": (
        ("Summits", "summits"),
        ("Workshops", "workshops"),
        ("Outreach", "outreach"),
        ("Community", "community"),
        ("Behind the scenes", "behind-the-scenes"),
    ),
}


def seed_content_configuration(apps, schema_editor):
    PageSettings = apps.get_model("content", "PageSettings")
    ContentCategory = apps.get_model("content", "ContentCategory")

    for section, heading, introduction in PAGE_SETTINGS:
        PageSettings.objects.get_or_create(
            section=section,
            defaults={
                "heading": heading,
                "introduction": introduction,
            },
        )

    for section, categories in CATEGORIES.items():
        for display_order, (name, slug) in enumerate(categories, start=1):
            ContentCategory.objects.get_or_create(
                section=section,
                slug=slug,
                defaults={
                    "name": name,
                    "display_order": display_order,
                    "is_active": True,
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            seed_content_configuration,
            migrations.RunPython.noop,
        ),
    ]
