from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0002_seed_page_settings_and_categories"),
    ]

    operations = [
        migrations.RenameField(
            model_name="newsarticle",
            old_name="body",
            new_name="body_markdown",
        ),
    ]
