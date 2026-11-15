from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions

from apps.accounts.permissions import IsContentManager, is_content_manager

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
    SiteSettings,
)
from .pagination import ContentPagination
from .serializers import (
    AboutPageSerializer,
    AboutPillarSerializer,
    ContentCategorySerializer,
    DonationOptionSerializer,
    EventsPageSerializer,
    GalleryItemSerializer,
    GalleryVideoSerializer,
    GetInvolvedPageSerializer,
    HomeFeatureSerializer,
    HomePageSerializer,
    ImpactStatisticSerializer,
    InvolvementFeatureSerializer,
    InvolvementStepSerializer,
    NewsArticleSerializer,
    PageSettingsSerializer,
    SiteSettingsSerializer,
)


CONTENT_FILTER_PARAMETERS = [
    OpenApiParameter(
        name="category",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter by category slug.",
    ),
    OpenApiParameter(
        name="status",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter by publication status. Content managers only.",
    ),
    OpenApiParameter(
        name="search",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Search textual content.",
    ),
]


class PublicReadContentManagerWriteMixin:
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)
        return (IsContentManager(),)


class PageSettingsView(PublicReadContentManagerWriteMixin, generics.RetrieveUpdateAPIView):
    serializer_class = PageSettingsSerializer
    section = None

    def get_object(self):
        return get_object_or_404(PageSettings, section=self.section)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get page heading and introduction")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update page heading and introduction",
        responses={
            200: PageSettingsSerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class NewsPageSettingsView(PageSettingsView):
    section = ContentSection.NEWS


class GalleryPageSettingsView(PageSettingsView):
    section = ContentSection.GALLERY


class CategoryListCreateView(
    PublicReadContentManagerWriteMixin,
    generics.ListCreateAPIView,
):
    serializer_class = ContentCategorySerializer
    pagination_class = None
    section = None

    def get_queryset(self):
        queryset = ContentCategory.objects.filter(section=self.section)
        if not is_content_manager(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            section=self.section,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @extend_schema(tags=["Content CMS"], summary="List content categories")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Create a content category",
        responses={
            201: ContentCategorySerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CategoryDetailView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    serializer_class = ContentCategorySerializer
    lookup_url_kwarg = "category_id"
    section = None

    def get_queryset(self):
        queryset = ContentCategory.objects.filter(section=self.section)
        if not is_content_manager(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get a content category")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update a content category",
        responses={
            200: ContentCategorySerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class NewsCategoryListCreateView(CategoryListCreateView):
    section = ContentSection.NEWS


class NewsCategoryDetailView(CategoryDetailView):
    section = ContentSection.NEWS


class GalleryCategoryListCreateView(CategoryListCreateView):
    section = ContentSection.GALLERY


class GalleryCategoryDetailView(CategoryDetailView):
    section = ContentSection.GALLERY


class NewsArticleListCreateView(
    PublicReadContentManagerWriteMixin,
    generics.ListCreateAPIView,
):
    serializer_class = NewsArticleSerializer
    pagination_class = ContentPagination

    def get_queryset(self):
        queryset = NewsArticle.objects.select_related(
            "category",
            "created_by",
            "updated_by",
        )
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        elif self.request.query_params.get("status"):
            queryset = queryset.filter(
                publication_status=self.request.query_params["status"]
            )
        if self.request.query_params.get("category"):
            queryset = queryset.filter(
                category__slug__iexact=self.request.query_params["category"]
            )
        if self.request.query_params.get("search"):
            query = self.request.query_params["search"].strip()
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(excerpt__icontains=query)
                | Q(body_markdown__icontains=query)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @extend_schema(
        tags=["Content CMS"],
        summary="List news articles",
        parameters=CONTENT_FILTER_PARAMETERS,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Create a news article",
        responses={
            201: NewsArticleSerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class NewsArticleDetailView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    serializer_class = NewsArticleSerializer
    lookup_field = "slug__iexact"
    lookup_url_kwarg = "article_slug"

    def get_queryset(self):
        queryset = NewsArticle.objects.select_related(
            "category",
            "created_by",
            "updated_by",
        )
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get a news article")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update a news article",
        responses={
            200: NewsArticleSerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class GalleryItemListCreateView(
    PublicReadContentManagerWriteMixin,
    generics.ListCreateAPIView,
):
    serializer_class = GalleryItemSerializer
    pagination_class = ContentPagination

    def get_queryset(self):
        queryset = GalleryItem.objects.select_related(
            "category",
            "created_by",
            "updated_by",
        )
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        elif self.request.query_params.get("status"):
            queryset = queryset.filter(
                publication_status=self.request.query_params["status"]
            )
        if self.request.query_params.get("category"):
            queryset = queryset.filter(
                category__slug__iexact=self.request.query_params["category"]
            )
        if self.request.query_params.get("search"):
            query = self.request.query_params["search"].strip()
            queryset = queryset.filter(
                Q(caption__icontains=query) | Q(alt_text__icontains=query)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @extend_schema(
        tags=["Content CMS"],
        summary="List gallery items",
        parameters=CONTENT_FILTER_PARAMETERS,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Create a gallery item",
        responses={
            201: GalleryItemSerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GalleryItemDetailView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    serializer_class = GalleryItemSerializer
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        queryset = GalleryItem.objects.select_related(
            "category",
            "created_by",
            "updated_by",
        )
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get a gallery item")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update a gallery item",
        responses={
            200: GalleryItemSerializer,
            403: OpenApiResponse(description="Content manager access required."),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class SingletonContentView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    lookup_field_name = "page_key"
    lookup_value = None

    def get_object(self):
        return get_object_or_404(
            self.get_queryset(),
            **{self.lookup_field_name: self.lookup_value},
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get structured page content")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update structured page content",
        responses={403: OpenApiResponse(description="Content manager access required.")},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class SiteSettingsView(SingletonContentView):
    serializer_class = SiteSettingsSerializer
    queryset = SiteSettings.objects.all()
    lookup_field_name = "site_key"
    lookup_value = "main"


class HomePageView(SingletonContentView):
    serializer_class = HomePageSerializer
    queryset = HomePage.objects.prefetch_related("features")
    lookup_value = "home"


class AboutPageView(SingletonContentView):
    serializer_class = AboutPageSerializer
    queryset = AboutPage.objects.prefetch_related("pillars")
    lookup_value = "about"


class GetInvolvedPageView(SingletonContentView):
    serializer_class = GetInvolvedPageSerializer
    queryset = GetInvolvedPage.objects.prefetch_related(
        "features",
        "donation_options",
        "steps",
    )
    lookup_value = "get_involved"


class EventsPageView(SingletonContentView):
    serializer_class = EventsPageSerializer
    queryset = EventsPage.objects.all()
    lookup_value = "events"


class ManagedItemListCreateView(
    PublicReadContentManagerWriteMixin,
    generics.ListCreateAPIView,
):
    pagination_class = None
    parent_model = None
    parent_field = None
    parent_key = None

    def get_queryset(self):
        queryset = super().get_queryset()
        if not is_content_manager(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        values = {
            "created_by": self.request.user,
            "updated_by": self.request.user,
        }
        if self.parent_model and self.parent_field:
            values[self.parent_field] = get_object_or_404(
                self.parent_model,
                page_key=self.parent_key,
            )
        serializer.save(**values)

    @extend_schema(tags=["Content CMS"], summary="List ordered page items")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Create an ordered page item",
        responses={403: OpenApiResponse(description="Content manager access required.")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ManagedItemDetailView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not is_content_manager(self.request.user):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get an ordered page item")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["Content CMS"],
        summary="Update an ordered page item",
        responses={403: OpenApiResponse(description="Content manager access required.")},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ImpactStatisticListCreateView(ManagedItemListCreateView):
    serializer_class = ImpactStatisticSerializer
    queryset = ImpactStatistic.objects.all()


class ImpactStatisticDetailView(ManagedItemDetailView):
    serializer_class = ImpactStatisticSerializer
    queryset = ImpactStatistic.objects.all()


class HomeFeatureListCreateView(ManagedItemListCreateView):
    serializer_class = HomeFeatureSerializer
    queryset = HomeFeature.objects.all()
    parent_model = HomePage
    parent_field = "page"
    parent_key = "home"


class HomeFeatureDetailView(ManagedItemDetailView):
    serializer_class = HomeFeatureSerializer
    queryset = HomeFeature.objects.all()


class AboutPillarListCreateView(ManagedItemListCreateView):
    serializer_class = AboutPillarSerializer
    queryset = AboutPillar.objects.all()
    parent_model = AboutPage
    parent_field = "page"
    parent_key = "about"


class AboutPillarDetailView(ManagedItemDetailView):
    serializer_class = AboutPillarSerializer
    queryset = AboutPillar.objects.all()


class InvolvementFeatureListCreateView(ManagedItemListCreateView):
    serializer_class = InvolvementFeatureSerializer
    queryset = InvolvementFeature.objects.all()
    parent_model = GetInvolvedPage
    parent_field = "page"
    parent_key = "get_involved"


class InvolvementFeatureDetailView(ManagedItemDetailView):
    serializer_class = InvolvementFeatureSerializer
    queryset = InvolvementFeature.objects.all()


class DonationOptionListCreateView(ManagedItemListCreateView):
    serializer_class = DonationOptionSerializer
    queryset = DonationOption.objects.all()
    parent_model = GetInvolvedPage
    parent_field = "page"
    parent_key = "get_involved"


class DonationOptionDetailView(ManagedItemDetailView):
    serializer_class = DonationOptionSerializer
    queryset = DonationOption.objects.all()


class InvolvementStepListCreateView(ManagedItemListCreateView):
    serializer_class = InvolvementStepSerializer
    queryset = InvolvementStep.objects.all()
    parent_model = GetInvolvedPage
    parent_field = "page"
    parent_key = "get_involved"


class InvolvementStepDetailView(ManagedItemDetailView):
    serializer_class = InvolvementStepSerializer
    queryset = InvolvementStep.objects.all()


class GalleryVideoListCreateView(
    PublicReadContentManagerWriteMixin,
    generics.ListCreateAPIView,
):
    serializer_class = GalleryVideoSerializer
    pagination_class = ContentPagination

    def get_queryset(self):
        queryset = GalleryVideo.objects.select_related("created_by", "updated_by")
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        elif self.request.query_params.get("status"):
            queryset = queryset.filter(
                publication_status=self.request.query_params["status"]
            )
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    @extend_schema(
        tags=["Content CMS"],
        summary="List gallery highlight videos",
        parameters=CONTENT_FILTER_PARAMETERS[1:],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Content CMS"], summary="Create a gallery highlight video")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GalleryVideoDetailView(
    PublicReadContentManagerWriteMixin,
    generics.RetrieveUpdateAPIView,
):
    serializer_class = GalleryVideoSerializer
    lookup_url_kwarg = "video_id"

    def get_queryset(self):
        queryset = GalleryVideo.objects.select_related("created_by", "updated_by")
        if not is_content_manager(self.request.user):
            queryset = queryset.publicly_visible()
        return queryset

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @extend_schema(tags=["Content CMS"], summary="Get a gallery highlight video")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["Content CMS"], summary="Update a gallery highlight video")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
