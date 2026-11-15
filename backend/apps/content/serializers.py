from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import (
    ContentCategory,
    ContentSection,
    GalleryItem,
    NewsArticle,
    PageSettings,
    PublicationStatus,
)


def convert_validation_error(error: DjangoValidationError):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": list(error.messages)}


class ModelValidationMixin:
    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            instance.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                convert_validation_error(error)
            ) from error
        instance.save()
        return instance


class PageSettingsSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = PageSettings
        fields = (
            "section",
            "heading",
            "introduction",
            "updated_at",
        )
        read_only_fields = ("section", "updated_at")


class ContentCategorySerializer(
    ModelValidationMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = ContentCategory
        fields = (
            "id",
            "section",
            "name",
            "slug",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "section",
            "created_at",
            "updated_at",
        )

    def validate_slug(self, value):
        return value.strip().lower()


class PublicationValidationMixin:
    section = None

    def validate(self, attributes):
        attributes = super().validate(attributes)
        instance = self.instance
        category = attributes.get(
            "category",
            instance.category if instance else None,
        )
        if category and category.section != self.section:
            raise serializers.ValidationError(
                {
                    "category": (
                        f"The category must belong to the {self.section} section."
                    )
                }
            )

        publication_status = attributes.get(
            "publication_status",
            instance.publication_status if instance else PublicationStatus.DRAFT,
        )
        published_at = attributes.get(
            "published_at",
            instance.published_at if instance else None,
        )
        if publication_status == PublicationStatus.PUBLISHED and not published_at:
            published_at = timezone.now()
            attributes["published_at"] = published_at
        if publication_status == PublicationStatus.SCHEDULED and not published_at:
            raise serializers.ValidationError(
                {"published_at": "A scheduled item requires a publication date."}
            )
        if (
            publication_status == PublicationStatus.SCHEDULED
            and published_at
            and published_at <= timezone.now()
            and (
                "publication_status" in attributes
                or "published_at" in attributes
            )
        ):
            raise serializers.ValidationError(
                {"published_at": "A scheduled publication date must be in the future."}
            )
        return attributes


class NewsArticleSerializer(
    PublicationValidationMixin,
    ModelValidationMixin,
    serializers.ModelSerializer,
):
    section = ContentSection.NEWS
    body_markdown = serializers.CharField(
        help_text=(
            "Original Markdown from the CMS editor. Inline images use URLs; "
            "clients must sanitize generated HTML."
        )
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "category",
            "category_name",
            "category_slug",
            "title",
            "slug",
            "excerpt",
            "body_markdown",
            "cover_image",
            "cover_alt_text",
            "publication_status",
            "published_at",
            "is_featured",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_slug(self, value):
        return value.strip().lower()


class GalleryItemSerializer(
    PublicationValidationMixin,
    ModelValidationMixin,
    serializers.ModelSerializer,
):
    section = ContentSection.GALLERY
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = GalleryItem
        fields = (
            "id",
            "category",
            "category_name",
            "category_slug",
            "image",
            "alt_text",
            "caption",
            "publication_status",
            "published_at",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )
