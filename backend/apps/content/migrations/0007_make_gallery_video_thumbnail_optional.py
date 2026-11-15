import apps.content.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content", "0006_rename_gallery_video_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="galleryvideo",
            name="thumbnail",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="content/gallery/videos/%Y/%m/",
                validators=(apps.content.models.validate_content_image_size,),
            ),
        ),
        migrations.AlterField(
            model_name="galleryvideo",
            name="thumbnail_alt_text",
            field=models.CharField(blank=True, max_length=250),
        ),
    ]
