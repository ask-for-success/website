from django.contrib import admin

from .models import (
    AboutPage,
    AboutPillar,
    ContentCategory,
    DonationOption,
    EventsPage,
    GalleryItem,
    GalleryVideo,
    GetInvolvedPage,
    HomeFeature,
    HomePage,
    ImpactStatistic,
    InvolvementFeature,
    InvolvementStep,
    NewsArticle,
    PageSettings,
    SiteSettings,
)


@admin.register(PageSettings)
class PageSettingsAdmin(admin.ModelAdmin):
    list_display = ("section", "heading", "updated_by", "updated_at")
    list_filter = ("section",)


@admin.register(ContentCategory)
class ContentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "display_order", "is_active")
    list_filter = ("section", "is_active")
    search_fields = ("name", "slug")
    ordering = ("section", "display_order", "name")


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "publication_status",
        "published_at",
        "is_featured",
    )
    list_filter = ("publication_status", "is_featured", "category")
    search_fields = ("title", "excerpt", "body_markdown")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_at", "title")


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = (
        "caption",
        "category",
        "publication_status",
        "published_at",
        "display_order",
    )
    list_filter = ("publication_status", "category")
    search_fields = ("caption", "alt_text")
    ordering = ("display_order", "-published_at")


admin.site.register(SiteSettings)
admin.site.register(HomePage)
admin.site.register(HomeFeature)
admin.site.register(AboutPage)
admin.site.register(AboutPillar)
admin.site.register(GetInvolvedPage)
admin.site.register(InvolvementFeature)
admin.site.register(DonationOption)
admin.site.register(InvolvementStep)
admin.site.register(EventsPage)
admin.site.register(ImpactStatistic)
admin.site.register(GalleryVideo)
