import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


MAX_CONTENT_IMAGE_SIZE = 10 * 1024 * 1024


def validate_content_image_size(image) -> None:
    if image.size > MAX_CONTENT_IMAGE_SIZE:
        raise ValidationError("The image must not exceed 10 MB.")


class ContentSection(models.TextChoices):
    NEWS = "news", "News"
    GALLERY = "gallery", "Gallery"


class PublicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class PageSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(
        max_length=16,
        choices=ContentSection.choices,
        unique=True,
    )
    heading = models.CharField(max_length=200)
    introduction = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_content_pages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_page_settings"
        ordering = ("section",)
        verbose_name_plural = "page settings"

    def clean(self) -> None:
        super().clean()
        self.heading = self.heading.strip()
        self.introduction = self.introduction.strip()

    def __str__(self) -> str:
        return f"{self.get_section_display()} page"


class ContentCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=16, choices=ContentSection.choices)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_content_categories",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_content_categories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_categories"
        ordering = ("section", "display_order", "name")
        verbose_name_plural = "content categories"
        constraints = (
            models.UniqueConstraint(
                models.F("section"),
                Lower("slug"),
                name="content_categories_section_slug_unique_ci",
            ),
            models.UniqueConstraint(
                models.F("section"),
                Lower("name"),
                name="content_categories_section_name_unique_ci",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        self.slug = self.slug.strip().lower()

    def __str__(self) -> str:
        return f"{self.get_section_display()}: {self.name}"


class NewsArticleQuerySet(models.QuerySet):
    def publicly_visible(self):
        now = timezone.now()
        return self.filter(
            category__is_active=True,
            publication_status__in=(
                PublicationStatus.PUBLISHED,
                PublicationStatus.SCHEDULED,
            ),
            published_at__lte=now,
        )


class NewsArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        ContentCategory,
        on_delete=models.PROTECT,
        related_name="news_articles",
    )
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240)
    excerpt = models.TextField(max_length=500)
    body_markdown = models.TextField()
    cover_image = models.ImageField(
        upload_to="content/news/%Y/%m/",
        validators=(validate_content_image_size,),
    )
    cover_alt_text = models.CharField(max_length=250)
    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_news_articles",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_news_articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NewsArticleQuerySet.as_manager()

    class Meta:
        db_table = "news_articles"
        ordering = ("-is_featured", "display_order", "-published_at", "-created_at")
        constraints = (
            models.UniqueConstraint(
                Lower("slug"),
                name="news_articles_slug_unique_ci",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.slug = self.slug.strip().lower()
        self.excerpt = self.excerpt.strip()
        self.cover_alt_text = self.cover_alt_text.strip()
        if self.category_id and self.category.section != ContentSection.NEWS:
            raise ValidationError(
                {"category": "The category must belong to the news section."}
            )
        if (
            self.publication_status
            in (PublicationStatus.SCHEDULED, PublicationStatus.PUBLISHED)
            and not self.published_at
        ):
            raise ValidationError(
                {
                    "published_at": (
                        "A publication date is required for scheduled or "
                        "published articles."
                    )
                }
            )

    def __str__(self) -> str:
        return self.title


class GalleryItemQuerySet(models.QuerySet):
    def publicly_visible(self):
        now = timezone.now()
        return self.filter(
            category__is_active=True,
            publication_status__in=(
                PublicationStatus.PUBLISHED,
                PublicationStatus.SCHEDULED,
            ),
            published_at__lte=now,
        )


class GalleryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        ContentCategory,
        on_delete=models.PROTECT,
        related_name="gallery_items",
    )
    image = models.ImageField(
        upload_to="content/gallery/%Y/%m/",
        validators=(validate_content_image_size,),
    )
    alt_text = models.CharField(max_length=250)
    caption = models.CharField(max_length=250, blank=True)
    publication_status = models.CharField(
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_gallery_items",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_gallery_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GalleryItemQuerySet.as_manager()

    class Meta:
        db_table = "gallery_items"
        ordering = ("display_order", "-published_at", "-created_at")

    def clean(self) -> None:
        super().clean()
        self.alt_text = self.alt_text.strip()
        self.caption = self.caption.strip()
        if self.category_id and self.category.section != ContentSection.GALLERY:
            raise ValidationError(
                {"category": "The category must belong to the gallery section."}
            )
        if (
            self.publication_status
            in (PublicationStatus.SCHEDULED, PublicationStatus.PUBLISHED)
            and not self.published_at
        ):
            raise ValidationError(
                {
                    "published_at": (
                        "A publication date is required for scheduled or "
                        "published gallery items."
                    )
                }
            )

    def __str__(self) -> str:
        return self.caption or self.alt_text
