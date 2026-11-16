from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="redoc",
    ),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/access/", include("apps.accounts.access_urls")),
    path(
        "api/v1/account-management/",
        include("apps.accounts.management_urls"),
    ),
    path("api/v1/administration/", include("apps.administration.urls")),
    path("api/v1/memberships/", include("apps.memberships.urls")),
    path("api/v1/organization/", include("apps.organization.urls")),
    path("api/v1/events/", include("apps.events.urls")),
    path("api/v1/content/", include("apps.content.urls")),
    path("api/v1/donations/", include("apps.donations.urls")),
    path("api/v1/recruitment/", include("apps.recruitment.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
]

if settings.DEBUG and settings.FILE_STORAGE_BACKEND == "filesystem":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
