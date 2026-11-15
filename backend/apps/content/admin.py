from django.contrib import admin

from .models import ContentCategory, GalleryItem, NewsArticle, PageSettings


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
