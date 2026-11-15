from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    AboutPage,
    AboutPillar,
    ContentCategory,
    ContentSection,
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
    PublicationStatus,
    SiteSettings,
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
            "hero_heading",
            "hero_introduction",
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


def visible_items(queryset, context):
    request = context.get("request")
    if not (
        request
        and request.user
        and request.user.is_authenticated
        and (
            request.user.is_superuser
            or request.user.has_perm("accounts.manage_content")
        )
    ):
        queryset = queryset.filter(is_active=True)
    return queryset


class ManagedItemSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        exclude = ("created_by", "updated_by")
        read_only_fields = ("id", "created_at", "updated_at")


class ImpactStatisticSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = ImpactStatistic


class HomeFeatureSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = HomeFeature
        exclude = ManagedItemSerializer.Meta.exclude + ("page",)


class AboutPillarSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = AboutPillar
        exclude = ManagedItemSerializer.Meta.exclude + ("page",)


class InvolvementFeatureSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = InvolvementFeature
        exclude = ManagedItemSerializer.Meta.exclude + ("page",)


class DonationOptionSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = DonationOption
        exclude = ManagedItemSerializer.Meta.exclude + ("page",)

    def validate_instructions(self, value):
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise serializers.ValidationError(
                "Instructions must be a list of non-empty text items."
            )
        return [item.strip() for item in value]


class InvolvementStepSerializer(ManagedItemSerializer):
    class Meta(ManagedItemSerializer.Meta):
        model = InvolvementStep
        exclude = ManagedItemSerializer.Meta.exclude + ("page",)


class EditablePageSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        exclude = ("updated_by",)
        read_only_fields = ("id", "page_key", "created_at", "updated_at")


class SiteSettingsSerializer(ModelValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ("updated_by",)
        read_only_fields = ("id", "site_key", "created_at", "updated_at")


class HomePageSerializer(EditablePageSerializer):
    features = serializers.SerializerMethodField()
    impact_statistics = serializers.SerializerMethodField()

    class Meta(EditablePageSerializer.Meta):
        model = HomePage

    @extend_schema_field(HomeFeatureSerializer(many=True))
    def get_features(self, instance):
        items = visible_items(instance.features.all(), self.context)
        return HomeFeatureSerializer(items, many=True).data

    @extend_schema_field(ImpactStatisticSerializer(many=True))
    def get_impact_statistics(self, instance):
        items = visible_items(ImpactStatistic.objects.all(), self.context)
        return ImpactStatisticSerializer(items, many=True).data


class AboutPageSerializer(EditablePageSerializer):
    pillars = serializers.SerializerMethodField()
    impact_statistics = serializers.SerializerMethodField()

    class Meta(EditablePageSerializer.Meta):
        model = AboutPage

    @extend_schema_field(AboutPillarSerializer(many=True))
    def get_pillars(self, instance):
        items = visible_items(instance.pillars.all(), self.context)
        return AboutPillarSerializer(items, many=True).data

    @extend_schema_field(ImpactStatisticSerializer(many=True))
    def get_impact_statistics(self, instance):
        items = visible_items(ImpactStatistic.objects.all(), self.context)
        return ImpactStatisticSerializer(items, many=True).data


class GetInvolvedPageSerializer(EditablePageSerializer):
    features = serializers.SerializerMethodField()
    donation_options = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()

    class Meta(EditablePageSerializer.Meta):
        model = GetInvolvedPage

    @extend_schema_field(InvolvementFeatureSerializer(many=True))
    def get_features(self, instance):
        items = visible_items(instance.features.all(), self.context)
        return InvolvementFeatureSerializer(items, many=True).data

    @extend_schema_field(DonationOptionSerializer(many=True))
    def get_donation_options(self, instance):
        items = visible_items(instance.donation_options.all(), self.context)
        return DonationOptionSerializer(items, many=True).data

    @extend_schema_field(InvolvementStepSerializer(many=True))
    def get_steps(self, instance):
        items = visible_items(instance.steps.all(), self.context)
        return InvolvementStepSerializer(items, many=True).data


class EventsPageSerializer(EditablePageSerializer):
    class Meta(EditablePageSerializer.Meta):
        model = EventsPage


class GalleryVideoSerializer(ModelValidationMixin, serializers.ModelSerializer):
    youtube_video_id = serializers.CharField(read_only=True)
    youtube_embed_url = serializers.CharField(read_only=True)
    youtube_thumbnail_url = serializers.CharField(read_only=True)

    class Meta:
        model = GalleryVideo
        fields = (
            "id",
            "title",
            "youtube_url",
            "youtube_video_id",
            "youtube_embed_url",
            "youtube_thumbnail_url",
            "thumbnail",
            "thumbnail_alt_text",
            "duration_label",
            "publication_status",
            "published_at",
            "display_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attributes):
        instance = self.instance
        publication_status = attributes.get(
            "publication_status",
            instance.publication_status if instance else PublicationStatus.DRAFT,
        )
        published_at = attributes.get(
            "published_at",
            instance.published_at if instance else None,
        )
        if publication_status == PublicationStatus.PUBLISHED and not published_at:
            attributes["published_at"] = timezone.now()
        elif publication_status == PublicationStatus.SCHEDULED:
            if not published_at:
                raise serializers.ValidationError(
                    {"published_at": "A scheduled video requires a publication date."}
                )
            if published_at <= timezone.now() and (
                "publication_status" in attributes or "published_at" in attributes
            ):
                raise serializers.ValidationError(
                    {"published_at": "A scheduled publication date must be in the future."}
                )
        return attributes
