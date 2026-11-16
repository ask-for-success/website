import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.email import build_email_settings


BASE_DIR = Path(__file__).resolve().parent.parent


def get_boolean(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


SECRET_KEY = os.getenv(
    "AFS_SECRET_KEY",
    "local-development-key-replace-before-production-2026",
)
DEBUG = get_boolean("AFS_DEBUG", True)
ALLOWED_HOSTS = get_list("AFS_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "storages",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts",
    "apps.administration",
    "apps.memberships",
    "apps.events",
    "apps.content",
    "apps.donations",
    "apps.organization",
    "apps.recruitment",
    "apps.audit",
    "apps.file_storage",
    "apps.email_delivery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.ActivityAuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("AFS_DB_NAME", "afs"),
        "USER": os.getenv("AFS_DB_USER", "afs"),
        "PASSWORD": os.getenv("AFS_DB_PASSWORD", "afs"),
        "HOST": os.getenv("AFS_DB_HOST", "database"),
        "PORT": os.getenv("AFS_DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

_email_settings = build_email_settings(os.environ)
EMAIL_PROVIDER = _email_settings["EMAIL_PROVIDER"]
EMAIL_BACKEND = _email_settings["EMAIL_BACKEND"]
DEFAULT_FROM_EMAIL = _email_settings["DEFAULT_FROM_EMAIL"]
EMAIL_HOST = _email_settings["EMAIL_HOST"]
EMAIL_PORT = _email_settings["EMAIL_PORT"]
EMAIL_HOST_USER = _email_settings["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = _email_settings["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = _email_settings["EMAIL_USE_TLS"]
EMAIL_USE_SSL = _email_settings["EMAIL_USE_SSL"]
EMAIL_TIMEOUT = _email_settings["EMAIL_TIMEOUT"]
SES_REGION = _email_settings["SES_REGION"]
SES_SMTP_HOST = _email_settings["SES_SMTP_HOST"]
PUBLIC_WEB_URL = os.getenv("AFS_PUBLIC_WEB_URL", "http://localhost:3000")

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"
FILE_STORAGE_BACKEND = os.getenv("AFS_STORAGE_BACKEND", "filesystem").lower()

if FILE_STORAGE_BACKEND not in {"filesystem", "seaweedfs"}:
    raise ImproperlyConfigured(
        "AFS_STORAGE_BACKEND must be either 'filesystem' or 'seaweedfs'."
    )

if FILE_STORAGE_BACKEND == "seaweedfs":
    SEAWEEDFS_ENDPOINT_URL = os.getenv("AFS_STORAGE_S3_ENDPOINT_URL", "").rstrip(
        "/"
    )
    SEAWEEDFS_PUBLIC_BASE_URL = os.getenv(
        "AFS_STORAGE_PUBLIC_BASE_URL",
        "",
    ).rstrip("/")
    SEAWEEDFS_ACCESS_KEY = os.getenv("AFS_STORAGE_ACCESS_KEY", "")
    SEAWEEDFS_SECRET_KEY = os.getenv("AFS_STORAGE_SECRET_KEY", "")
    SEAWEEDFS_PUBLIC_BUCKET = os.getenv(
        "AFS_STORAGE_PUBLIC_BUCKET",
        "afs-public-media",
    )
    SEAWEEDFS_PRIVATE_BUCKET = os.getenv(
        "AFS_STORAGE_PRIVATE_BUCKET",
        "afs-private-files",
    )
    SEAWEEDFS_REGION = os.getenv("AFS_STORAGE_REGION", "us-east-1")
    required_storage_settings = {
        "AFS_STORAGE_S3_ENDPOINT_URL": SEAWEEDFS_ENDPOINT_URL,
        "AFS_STORAGE_PUBLIC_BASE_URL": SEAWEEDFS_PUBLIC_BASE_URL,
        "AFS_STORAGE_ACCESS_KEY": SEAWEEDFS_ACCESS_KEY,
        "AFS_STORAGE_SECRET_KEY": SEAWEEDFS_SECRET_KEY,
    }
    missing_storage_settings = [
        name for name, value in required_storage_settings.items() if not value
    ]
    if missing_storage_settings:
        raise ImproperlyConfigured(
            "Missing SeaweedFS settings: "
            + ", ".join(sorted(missing_storage_settings))
        )

    common_s3_options = {
        "access_key": SEAWEEDFS_ACCESS_KEY,
        "secret_key": SEAWEEDFS_SECRET_KEY,
        "endpoint_url": SEAWEEDFS_ENDPOINT_URL,
        "region_name": SEAWEEDFS_REGION,
        "addressing_style": "path",
        "signature_version": "s3v4",
        "default_acl": None,
        "file_overwrite": False,
        "max_memory_size": 10 * 1024 * 1024,
    }
    STORAGES = {
        "default": {
            "BACKEND": "apps.file_storage.backends.PublicMediaStorage",
            "OPTIONS": {
                **common_s3_options,
                "bucket_name": SEAWEEDFS_PUBLIC_BUCKET,
                "querystring_auth": False,
            },
        },
        "private": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                **common_s3_options,
                "bucket_name": SEAWEEDFS_PRIVATE_BUCKET,
                "querystring_auth": True,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_URL = f"{SEAWEEDFS_PUBLIC_BASE_URL}/"
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": MEDIA_ROOT,
                "base_url": MEDIA_URL,
            },
        },
        "private": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": PRIVATE_MEDIA_ROOT,
                "base_url": None,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Ask For Success API",
    "DESCRIPTION": (
        "Backend API contract for the Ask For Success platform. "
        "Only implemented endpoints are included."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
    "ENUM_NAME_OVERRIDES": {
        "EventPublicationStatus": "apps.events.models.PublicationStatus",
        "ContentPublicationStatus": "apps.content.models.PublicationStatus",
        "ContentSection": "apps.content.models.ContentSection",
        "DonationType": "apps.donations.models.DonationType",
        "EmailDeliveryStatus": "apps.events.models.EmailDeliveryStatus",
        "InvolvementFeatureSection": (
            "apps.content.models.InvolvementFeatureSection"
        ),
        "MembershipStatus": "apps.memberships.models.MembershipStatus",
        "OnboardingStatus": "apps.memberships.models.OnboardingStatus",
        "MembershipInvitationStatus": (
            "apps.memberships.models.MembershipInvitationStatus"
        ),
        "AccountInvitationPurpose": (
            "apps.accounts.models.AccountInvitationPurpose"
        ),
        "EventRegistrationStatus": (
            "apps.events.models.EventRegistrationStatus"
        ),
        "EventRegistrationSource": (
            "apps.events.models.EventRegistrationSource"
        ),
        "EventNotificationType": (
            "apps.events.models.EventNotificationType"
        ),
        "RecruitmentFormStatus": (
            "apps.recruitment.models.RecruitmentFormStatus"
        ),
        "RecruitmentQuestionType": (
            "apps.recruitment.models.RecruitmentQuestionType"
        ),
        "RecruitmentOpportunityStatus": (
            "apps.recruitment.models.OpportunityStatus"
        ),
        "RecruitmentApplicationStatus": (
            "apps.recruitment.models.ApplicationStatus"
        ),
        "RecruitmentDecisionEmailStatus": (
            "apps.recruitment.models.DecisionEmailStatus"
        ),
        "RecruitmentOfferResponse": "apps.recruitment.models.OfferResponse",
        "AuditDomain": "apps.audit.models.AuditDomain",
        "AuditAction": "apps.audit.models.AuditAction",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "CHECK_REVOKE_TOKEN": True,
    "REVOKE_TOKEN_CLAIM": "password_hash",
}
