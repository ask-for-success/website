from io import StringIO
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from config.email import (
    CONSOLE_EMAIL_BACKEND,
    SMTP_EMAIL_BACKEND,
    build_email_settings,
)


class EmailConfigurationTests(SimpleTestCase):
    def ses_environment(self, **overrides):
        environment = {
            "AFS_EMAIL_PROVIDER": "ses",
            "AFS_DEFAULT_FROM_EMAIL": "no-reply@askforsuccess.org",
            "AFS_SES_REGION": "eu-west-3",
            "AFS_SES_SMTP_USERNAME": "smtp-user",
            "AFS_SES_SMTP_PASSWORD": "smtp-password",
        }
        environment.update(overrides)
        return environment

    def test_console_provider_is_the_safe_default(self):
        configuration = build_email_settings({})

        self.assertEqual(configuration["EMAIL_PROVIDER"], "console")
        self.assertEqual(configuration["EMAIL_BACKEND"], CONSOLE_EMAIL_BACKEND)
        self.assertFalse(configuration["EMAIL_USE_TLS"])

    def test_ses_provider_uses_region_endpoint_and_starttls(self):
        configuration = build_email_settings(self.ses_environment())

        self.assertEqual(configuration["EMAIL_BACKEND"], SMTP_EMAIL_BACKEND)
        self.assertEqual(
            configuration["EMAIL_HOST"],
            "email-smtp.eu-west-3.amazonaws.com",
        )
        self.assertEqual(configuration["EMAIL_PORT"], 587)
        self.assertTrue(configuration["EMAIL_USE_TLS"])
        self.assertFalse(configuration["EMAIL_USE_SSL"])
        self.assertEqual(configuration["EMAIL_TIMEOUT"], 10)

    def test_ses_provider_requires_region_credentials_and_sender(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_DEFAULT_FROM_EMAIL, AFS_SES_REGION, "
            "AFS_SES_SMTP_PASSWORD, AFS_SES_SMTP_USERNAME",
        ):
            build_email_settings({"AFS_EMAIL_PROVIDER": "ses"})

    def test_ses_provider_rejects_invalid_sender(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_DEFAULT_FROM_EMAIL must be a valid email address",
        ):
            build_email_settings(
                self.ses_environment(AFS_DEFAULT_FROM_EMAIL="not-an-email")
            )

    def test_ses_provider_rejects_non_starttls_port(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_SES_SMTP_PORT must be 587 or 2587",
        ):
            build_email_settings(
                self.ses_environment(AFS_SES_SMTP_PORT="465")
            )

    def test_ses_provider_rejects_url_as_smtp_host(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_SES_SMTP_HOST must be an SMTP hostname",
        ):
            build_email_settings(
                self.ses_environment(
                    AFS_SES_SMTP_HOST="https://email-smtp.example.com/path"
                )
            )

    def test_email_timeout_must_be_positive(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_EMAIL_TIMEOUT must be a positive integer",
        ):
            build_email_settings({"AFS_EMAIL_TIMEOUT": "0"})

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "AFS_EMAIL_PROVIDER must be either 'console' or 'ses'",
        ):
            build_email_settings({"AFS_EMAIL_PROVIDER": "unknown"})


@override_settings(
    EMAIL_PROVIDER="console",
    EMAIL_BACKEND=CONSOLE_EMAIL_BACKEND,
    DEFAULT_FROM_EMAIL="no-reply@askforsuccess.local",
)
class VerifyEmailDeliveryCommandTests(SimpleTestCase):
    @patch(
        "apps.email_delivery.management.commands."
        "verify_email_delivery.get_connection"
    )
    def test_connection_is_opened_and_closed_without_sending(self, connection_factory):
        connection = connection_factory.return_value
        output = StringIO()

        call_command("verify_email_delivery", stdout=output)

        connection.open.assert_called_once_with()
        connection.send_messages.assert_not_called()
        connection.close.assert_called_once_with()
        self.assertIn("Email connection opened successfully", output.getvalue())

    @patch(
        "apps.email_delivery.management.commands."
        "verify_email_delivery.get_connection"
    )
    def test_explicit_recipient_sends_one_test_message(self, connection_factory):
        connection = connection_factory.return_value
        connection.send_messages.return_value = 1
        output = StringIO()

        call_command(
            "verify_email_delivery",
            send_to="recipient@example.com",
            stdout=output,
        )

        messages = connection.send_messages.call_args.args[0]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].to, ["recipient@example.com"])
        self.assertEqual(
            messages[0].subject,
            "Ask For Success email delivery test",
        )
        connection.close.assert_called_once_with()
        self.assertIn("One test message was accepted", output.getvalue())

    @patch(
        "apps.email_delivery.management.commands."
        "verify_email_delivery.get_connection"
    )
    def test_connection_failure_is_reported_without_sending(self, connection_factory):
        connection = Mock()
        connection.open.side_effect = OSError("network unavailable")
        connection_factory.return_value = connection

        with self.assertRaisesMessage(
            CommandError,
            "Email delivery verification failed: network unavailable",
        ):
            call_command("verify_email_delivery", stdout=StringIO())

        connection.close.assert_called_once_with()

    def test_invalid_recipient_is_rejected_before_connecting(self):
        with self.assertRaisesMessage(
            CommandError,
            "--send-to must be a valid email address",
        ):
            call_command(
                "verify_email_delivery",
                send_to="not-an-email",
                stdout=StringIO(),
            )
