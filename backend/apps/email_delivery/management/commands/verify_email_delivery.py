from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Open the configured email connection and optionally send one explicit "
        "delivery test."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-to",
            dest="recipient",
            help=(
                "Send one test message to this address after the connection "
                "check succeeds."
            ),
        )

    def handle(self, *args, **options):
        recipient = options.get("recipient")
        if recipient:
            try:
                validate_email(recipient)
            except ValidationError as error:
                raise CommandError(
                    "--send-to must be a valid email address."
                ) from error

        self.stdout.write(
            f"Email provider: {settings.EMAIL_PROVIDER}; "
            f"backend: {settings.EMAIL_BACKEND}; "
            f"sender: {settings.DEFAULT_FROM_EMAIL}."
        )

        connection = None
        try:
            connection = get_connection(fail_silently=False)
            connection.open()
            self.stdout.write(
                self.style.SUCCESS("Email connection opened successfully.")
            )

            if recipient:
                message = EmailMessage(
                    subject="Ask For Success email delivery test",
                    body=(
                        "This message confirms that the Ask For Success backend "
                        "can deliver email through its configured provider.\n\n"
                        f"Generated at {timezone.now().isoformat()}."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient],
                    connection=connection,
                )
                sent_count = message.send(fail_silently=False)
                if sent_count != 1:
                    raise CommandError(
                        "The provider did not confirm delivery of the test message."
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"One test message was accepted for {recipient}."
                    )
                )
        except CommandError:
            raise
        except Exception as error:
            raise CommandError(
                f"Email delivery verification failed: {error}"
            ) from error
        finally:
            if connection is not None:
                connection.close()
