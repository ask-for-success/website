import re
import uuid
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


MAX_CONTENT_IMAGE_SIZE = 10 * 1024 * 1024
YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_content_image_size(image) -> None:
    if image.size > MAX_CONTENT_IMAGE_SIZE:
        raise ValidationError("The image must not exceed 10 MB.")


def validate_cms_link(value: str) -> None:
    if not value:
        return
    if value.startswith("/") and not value.startswith("//"):
        return
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return
    raise ValidationError(
        "Use an internal path or a complete HTTP or HTTPS URL."
    )


def extract_youtube_video_id(value: str) -> str | None:
    if not value:
        return None

    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        return None

    hostname = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname in {"youtu.be", "www.youtu.be"}:
        candidate = path_parts[0] if path_parts else ""
    elif hostname in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }:
        if parsed.path.rstrip("/") == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {
            "embed",
            "live",
            "shorts",
        }:
            candidate = path_parts[1]
        else:
            candidate = ""
    else:
        candidate = ""

    if not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate


def validate_youtube_url(value: str) -> None:
    if extract_youtube_video_id(value) is None:
        raise ValidationError(
            "Use a valid YouTube watch, share, Shorts, live, or embed URL."
        )


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
    hero_heading = models.CharField(max_length=200, blank=True)
    hero_introduction = models.TextField(blank=True)
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
        self.hero_heading = self.hero_heading.strip()
        self.hero_introduction = self.hero_introduction.strip()

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


class SiteSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site_key = models.CharField(max_length=32, unique=True, default="main")
    organization_name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=250, blank=True)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40)
    contact_location = models.CharField(max_length=250)
    tiktok_url = models.URLField(max_length=500, blank=True)
    youtube_url = models.URLField(max_length=500, blank=True)
    instagram_url = models.URLField(max_length=500, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_site_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "site_settings"
        verbose_name_plural = "site settings"

    def clean(self) -> None:
        super().clean()
        self.organization_name = self.organization_name.strip()
        self.tagline = self.tagline.strip()
        self.contact_phone = self.contact_phone.strip()
        self.contact_location = self.contact_location.strip()

    def __str__(self) -> str:
        return self.organization_name


class EditablePageBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page_key = models.CharField(max_length=32, unique=True, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_%(class)s_pages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class HomePage(EditablePageBase):
    hero_heading = models.CharField(max_length=250)
    hero_highlight = models.CharField(max_length=150, blank=True)
    hero_body = models.TextField()
    hero_image = models.ImageField(
        upload_to="content/pages/home/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    hero_image_alt_text = models.CharField(max_length=250, blank=True)
    primary_cta_label = models.CharField(max_length=100)
    primary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    secondary_cta_label = models.CharField(max_length=100)
    secondary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    about_heading = models.CharField(max_length=200)
    about_body = models.TextField()
    about_image = models.ImageField(
        upload_to="content/pages/home/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    about_image_alt_text = models.CharField(max_length=250, blank=True)
    about_cta_label = models.CharField(max_length=100)
    about_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    involvement_heading = models.CharField(max_length=200)
    involvement_subheading = models.CharField(max_length=250, blank=True)
    involvement_body = models.TextField(blank=True)
    events_heading = models.CharField(max_length=200)
    events_subheading = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "home_page_content"

    def clean(self) -> None:
        super().clean()
        if self.hero_image and not self.hero_image_alt_text.strip():
            raise ValidationError(
                {"hero_image_alt_text": "Alternative text is required."}
            )
        if self.about_image and not self.about_image_alt_text.strip():
            raise ValidationError(
                {"about_image_alt_text": "Alternative text is required."}
            )

    def __str__(self) -> str:
        return "Home page"


class AboutPage(EditablePageBase):
    hero_heading = models.CharField(max_length=250)
    hero_highlight = models.CharField(max_length=150, blank=True)
    hero_body = models.TextField()
    hero_image = models.ImageField(
        upload_to="content/pages/about/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    hero_image_alt_text = models.CharField(max_length=250, blank=True)
    mission_heading = models.CharField(max_length=200)
    mission_subheading = models.CharField(max_length=250, blank=True)
    mission_body = models.TextField()
    pillars_heading = models.CharField(max_length=200)
    pillars_subheading = models.CharField(max_length=250, blank=True)
    pillars_cta_label = models.CharField(max_length=100, blank=True)
    pillars_cta_url = models.CharField(
        max_length=500,
        blank=True,
        validators=(validate_cms_link,),
    )
    story_heading = models.CharField(max_length=200)
    story_subheading = models.CharField(max_length=250, blank=True)
    story_body = models.TextField()
    story_image = models.ImageField(
        upload_to="content/pages/about/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    story_image_alt_text = models.CharField(max_length=250, blank=True)
    closing_heading = models.CharField(max_length=200)
    closing_body = models.TextField()
    primary_cta_label = models.CharField(max_length=100)
    primary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    secondary_cta_label = models.CharField(max_length=100)
    secondary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )

    class Meta:
        db_table = "about_page_content"

    def clean(self) -> None:
        super().clean()
        if self.hero_image and not self.hero_image_alt_text.strip():
            raise ValidationError(
                {"hero_image_alt_text": "Alternative text is required."}
            )
        if self.story_image and not self.story_image_alt_text.strip():
            raise ValidationError(
                {"story_image_alt_text": "Alternative text is required."}
            )

    def __str__(self) -> str:
        return "About page"


class GetInvolvedPage(EditablePageBase):
    hero_heading = models.CharField(max_length=250)
    hero_highlight = models.CharField(max_length=150, blank=True)
    hero_body = models.TextField()
    hero_image = models.ImageField(
        upload_to="content/pages/get-involved/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    hero_image_alt_text = models.CharField(max_length=250, blank=True)
    primary_cta_label = models.CharField(max_length=100)
    primary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    secondary_cta_label = models.CharField(max_length=100)
    secondary_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    volunteer_heading = models.CharField(max_length=200)
    volunteer_subheading = models.CharField(max_length=250, blank=True)
    volunteer_body = models.TextField()
    volunteer_image = models.ImageField(
        upload_to="content/pages/get-involved/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    volunteer_image_alt_text = models.CharField(max_length=250, blank=True)
    volunteer_cta_label = models.CharField(max_length=100)
    volunteer_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    partner_heading = models.CharField(max_length=200)
    partner_subheading = models.CharField(max_length=250, blank=True)
    partner_body = models.TextField()
    partner_image = models.ImageField(
        upload_to="content/pages/get-involved/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    partner_image_alt_text = models.CharField(max_length=250, blank=True)
    partner_cta_label = models.CharField(max_length=100)
    partner_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    donation_heading = models.CharField(max_length=200)
    donation_subheading = models.CharField(max_length=250, blank=True)
    contact_prompt = models.TextField(blank=True)
    contact_cta_label = models.CharField(max_length=100, blank=True)
    contact_cta_url = models.CharField(
        max_length=500,
        blank=True,
        validators=(validate_cms_link,),
    )
    process_heading = models.CharField(max_length=200)
    process_subheading = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "get_involved_page_content"

    def clean(self) -> None:
        super().clean()
        image_pairs = (
            ("hero_image", "hero_image_alt_text"),
            ("volunteer_image", "volunteer_image_alt_text"),
            ("partner_image", "partner_image_alt_text"),
        )
        errors = {}
        for image_field, alt_field in image_pairs:
            if getattr(self, image_field) and not getattr(self, alt_field).strip():
                errors[alt_field] = "Alternative text is required."
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return "Get involved page"


class EventsPage(EditablePageBase):
    hero_heading = models.CharField(max_length=250)
    hero_highlight = models.CharField(max_length=150, blank=True)
    hero_body = models.TextField()
    hero_image = models.ImageField(
        upload_to="content/pages/events/",
        validators=(validate_content_image_size,),
        null=True,
        blank=True,
    )
    hero_image_alt_text = models.CharField(max_length=250, blank=True)
    hero_cta_label = models.CharField(max_length=100)
    hero_cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )
    next_heading = models.CharField(max_length=200)
    next_subheading = models.CharField(max_length=250, blank=True)
    upcoming_heading = models.CharField(max_length=200)
    upcoming_subheading = models.CharField(max_length=250, blank=True)
    past_heading = models.CharField(max_length=200)
    past_subheading = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "events_page_content"

    def clean(self) -> None:
        super().clean()
        if self.hero_image and not self.hero_image_alt_text.strip():
            raise ValidationError(
                {"hero_image_alt_text": "Alternative text is required."}
            )

    def __str__(self) -> str:
        return "Events page"


class ManagedOrderedItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_%(class)s_items",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_%(class)s_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("display_order", "created_at")


class ImpactStatistic(ManagedOrderedItem):
    value = models.CharField(max_length=50)
    label = models.CharField(max_length=150)

    class Meta(ManagedOrderedItem.Meta):
        db_table = "impact_statistics"

    def __str__(self) -> str:
        return f"{self.value} {self.label}"


class HomeFeature(ManagedOrderedItem):
    page = models.ForeignKey(
        HomePage,
        on_delete=models.CASCADE,
        related_name="features",
    )
    icon_key = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=150)
    body = models.TextField()
    cta_label = models.CharField(max_length=100)
    cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )

    class Meta(ManagedOrderedItem.Meta):
        db_table = "home_features"

    def __str__(self) -> str:
        return self.title


class AboutPillar(ManagedOrderedItem):
    page = models.ForeignKey(
        AboutPage,
        on_delete=models.CASCADE,
        related_name="pillars",
    )
    icon_key = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=150)
    body = models.TextField()

    class Meta(ManagedOrderedItem.Meta):
        db_table = "about_pillars"

    def __str__(self) -> str:
        return self.title


class InvolvementFeatureSection(models.TextChoices):
    VOLUNTEER = "volunteer", "Volunteer"
    PARTNER = "partner", "Partner"


class InvolvementFeature(ManagedOrderedItem):
    page = models.ForeignKey(
        GetInvolvedPage,
        on_delete=models.CASCADE,
        related_name="features",
    )
    section = models.CharField(
        max_length=16,
        choices=InvolvementFeatureSection.choices,
    )
    icon_key = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)

    class Meta(ManagedOrderedItem.Meta):
        db_table = "involvement_features"
        ordering = ("section", "display_order", "created_at")

    def __str__(self) -> str:
        return self.title


class DonationOption(ManagedOrderedItem):
    page = models.ForeignKey(
        GetInvolvedPage,
        on_delete=models.CASCADE,
        related_name="donation_options",
    )
    title = models.CharField(max_length=150)
    instructions = models.JSONField(default=list)
    cta_label = models.CharField(max_length=100)
    cta_url = models.CharField(
        max_length=500,
        validators=(validate_cms_link,),
    )

    class Meta(ManagedOrderedItem.Meta):
        db_table = "donation_options"

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.instructions, list) or not all(
            isinstance(item, str) and item.strip()
            for item in self.instructions
        ):
            raise ValidationError(
                {"instructions": "Instructions must be a list of text items."}
            )

    def __str__(self) -> str:
        return self.title


class InvolvementStep(ManagedOrderedItem):
    page = models.ForeignKey(
        GetInvolvedPage,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    title = models.CharField(max_length=150)
    body = models.TextField()

    class Meta(ManagedOrderedItem.Meta):
        db_table = "involvement_steps"

    def __str__(self) -> str:
        return self.title


class GalleryVideoQuerySet(models.QuerySet):
    def publicly_visible(self):
        now = timezone.now()
        return self.filter(
            publication_status__in=(
                PublicationStatus.PUBLISHED,
                PublicationStatus.SCHEDULED,
            ),
            published_at__lte=now,
        )


class GalleryVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=220)
    youtube_url = models.URLField(
        max_length=500,
        validators=(validate_youtube_url,),
    )
    thumbnail = models.ImageField(
        upload_to="content/gallery/videos/%Y/%m/",
        validators=(validate_content_image_size,),
        blank=True,
        null=True,
    )
    thumbnail_alt_text = models.CharField(max_length=250, blank=True)
    duration_label = models.CharField(max_length=50, blank=True)
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
        related_name="created_gallery_videos",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_gallery_videos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = GalleryVideoQuerySet.as_manager()

    class Meta:
        db_table = "gallery_videos"
        ordering = ("display_order", "-published_at", "-created_at")

    def clean(self) -> None:
        super().clean()
        self.title = self.title.strip()
        self.thumbnail_alt_text = self.thumbnail_alt_text.strip()
        if self.thumbnail and not self.thumbnail_alt_text:
            raise ValidationError(
                {
                    "thumbnail_alt_text": (
                        "Alternative text is required when a custom thumbnail "
                        "is uploaded."
                    )
                }
            )
        video_id = extract_youtube_video_id(self.youtube_url)
        if video_id:
            self.youtube_url = (
                f"https://www.youtube.com/watch?v={video_id}"
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
                        "published gallery videos."
                    )
                }
            )

    def __str__(self) -> str:
        return self.title

    @property
    def youtube_video_id(self) -> str:
        return extract_youtube_video_id(self.youtube_url) or ""

    @property
    def youtube_embed_url(self) -> str:
        if not self.youtube_video_id:
            return ""
        return (
            "https://www.youtube-nocookie.com/embed/"
            f"{self.youtube_video_id}"
        )

    @property
    def youtube_thumbnail_url(self) -> str:
        if not self.youtube_video_id:
            return ""
        return f"https://i.ytimg.com/vi/{self.youtube_video_id}/hqdefault.jpg"
