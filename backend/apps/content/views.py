from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions

from apps.accounts.permissions import IsContentManager, is_content_manager

from .models import (
    ContentCategory,
    ContentSection,
    GalleryItem,
    NewsArticle,
    PageSettings,
)
from .pagination import ContentPagination
from .serializers import (
    ContentCategorySerializer,
    GalleryItemSerializer,
    NewsArticleSerializer,
    PageSettingsSerializer,
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
