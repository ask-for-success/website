import apps.content.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0005_seed_structured_pages"),
    ]

    operations = [
        migrations.RenameField(
            model_name="galleryvideo",
            old_name="video_url",
            new_name="youtube_url",
        ),
        migrations.AlterField(
            model_name="galleryvideo",
            name="youtube_url",
            field=models.URLField(
                max_length=500,
                validators=(apps.content.models.validate_youtube_url,),
            ),
        ),
    ]
