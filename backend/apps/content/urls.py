from django.urls import path

from .views import (
    GalleryCategoryDetailView,
    GalleryCategoryListCreateView,
    GalleryItemDetailView,
    GalleryItemListCreateView,
    GalleryPageSettingsView,
    NewsArticleDetailView,
    NewsArticleListCreateView,
    NewsCategoryDetailView,
    NewsCategoryListCreateView,
    NewsPageSettingsView,
)


app_name = "content"

urlpatterns = [
    path("pages/news/", NewsPageSettingsView.as_view(), name="news_page"),
    path(
        "pages/gallery/",
        GalleryPageSettingsView.as_view(),
        name="gallery_page",
    ),
    path(
        "news/categories/",
        NewsCategoryListCreateView.as_view(),
        name="news_category_list_create",
    ),
    path(
        "news/categories/<uuid:category_id>/",
        NewsCategoryDetailView.as_view(),
        name="news_category_detail",
    ),
    path("news/", NewsArticleListCreateView.as_view(), name="news_list_create"),
    path(
        "news/<slug:article_slug>/",
        NewsArticleDetailView.as_view(),
        name="news_detail",
    ),
    path(
        "gallery/categories/",
        GalleryCategoryListCreateView.as_view(),
        name="gallery_category_list_create",
    ),
    path(
        "gallery/categories/<uuid:category_id>/",
        GalleryCategoryDetailView.as_view(),
        name="gallery_category_detail",
    ),
    path(
        "gallery/",
        GalleryItemListCreateView.as_view(),
        name="gallery_list_create",
    ),
    path(
        "gallery/<uuid:item_id>/",
        GalleryItemDetailView.as_view(),
        name="gallery_detail",
    ),
]
