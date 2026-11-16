import re
from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email


CONSOLE_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
SUPPORTED_EMAIL_PROVIDERS = {"console", "ses"}
SES_STARTTLS_PORTS = {587, 2587}


def _positive_integer(
    environment: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw_value = environment.get(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ImproperlyConfigured(f"{name} must be a positive integer.") from error
    if value <= 0:
        raise ImproperlyConfigured(f"{name} must be a positive integer.")
    return value


def _validate_sender(address: str) -> None:
    try:
        validate_email(address)
    except ValidationError as error:
        raise ImproperlyConfigured(
            "AFS_DEFAULT_FROM_EMAIL must be a valid email address."
        ) from error


def build_email_settings(environment: Mapping[str, str]) -> dict[str, object]:
    provider = environment.get("AFS_EMAIL_PROVIDER", "console").strip().lower()
    if provider not in SUPPORTED_EMAIL_PROVIDERS:
        raise ImproperlyConfigured(
            "AFS_EMAIL_PROVIDER must be either 'console' or 'ses'."
        )

    timeout = _positive_integer(environment, "AFS_EMAIL_TIMEOUT", 10)
    if provider == "console":
        return {
            "EMAIL_PROVIDER": provider,
            "EMAIL_BACKEND": CONSOLE_EMAIL_BACKEND,
            "DEFAULT_FROM_EMAIL": environment.get(
                "AFS_DEFAULT_FROM_EMAIL",
                "no-reply@askforsuccess.local",
            ).strip(),
            "EMAIL_HOST": "",
            "EMAIL_PORT": 587,
            "EMAIL_HOST_USER": "",
            "EMAIL_HOST_PASSWORD": "",
            "EMAIL_USE_TLS": False,
            "EMAIL_USE_SSL": False,
            "EMAIL_TIMEOUT": timeout,
            "SES_REGION": "",
            "SES_SMTP_HOST": "",
        }

    required_values = {
        "AFS_SES_REGION": environment.get("AFS_SES_REGION", "").strip(),
        "AFS_SES_SMTP_USERNAME": environment.get(
            "AFS_SES_SMTP_USERNAME",
            "",
        ).strip(),
        "AFS_SES_SMTP_PASSWORD": environment.get(
            "AFS_SES_SMTP_PASSWORD",
            "",
        ).strip(),
        "AFS_DEFAULT_FROM_EMAIL": environment.get(
            "AFS_DEFAULT_FROM_EMAIL",
            "",
        ).strip(),
    }
    missing_values = [
        name for name, value in required_values.items() if not value
    ]
    if missing_values:
        raise ImproperlyConfigured(
            "Missing Amazon SES settings: " + ", ".join(sorted(missing_values))
        )

    region = required_values["AFS_SES_REGION"]
    if not re.fullmatch(r"[a-z0-9-]+", region):
        raise ImproperlyConfigured(
            "AFS_SES_REGION may contain only lowercase letters, numbers, and hyphens."
        )

    sender = required_values["AFS_DEFAULT_FROM_EMAIL"]
    _validate_sender(sender)

    configured_smtp_host = environment.get("AFS_SES_SMTP_HOST", "").strip()
    smtp_host = configured_smtp_host or f"email-smtp.{region}.amazonaws.com"
    if (
        not smtp_host
        or "://" in smtp_host
        or "/" in smtp_host
        or any(character.isspace() for character in smtp_host)
    ):
        raise ImproperlyConfigured(
            "AFS_SES_SMTP_HOST must be an SMTP hostname without a URL scheme or path."
        )

    smtp_port = _positive_integer(environment, "AFS_SES_SMTP_PORT", 587)
    if smtp_port not in SES_STARTTLS_PORTS:
        raise ImproperlyConfigured(
            "AFS_SES_SMTP_PORT must be 587 or 2587 for STARTTLS."
        )

    return {
        "EMAIL_PROVIDER": provider,
        "EMAIL_BACKEND": SMTP_EMAIL_BACKEND,
        "DEFAULT_FROM_EMAIL": sender,
        "EMAIL_HOST": smtp_host,
        "EMAIL_PORT": smtp_port,
        "EMAIL_HOST_USER": required_values["AFS_SES_SMTP_USERNAME"],
        "EMAIL_HOST_PASSWORD": required_values["AFS_SES_SMTP_PASSWORD"],
        "EMAIL_USE_TLS": True,
        "EMAIL_USE_SSL": False,
        "EMAIL_TIMEOUT": timeout,
        "SES_REGION": region,
        "SES_SMTP_HOST": smtp_host,
    }
