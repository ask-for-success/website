from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import AcknowledgementEmailStatus, DonationSubmission


def send_donation_acknowledgement(submission: DonationSubmission) -> None:
    try:
        message = EmailMessage(
            subject="We received your donation interest",
            body=(
                f"Hello {submission.first_name},\n\n"
                "Thank you for contacting Ask For Success about making a "
                f"{submission.get_donation_type_display().lower()} donation. "
                "We received your information and our team will contact you "
                "later with the next steps.\n\n"
                "Your support matters to us."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[submission.email],
        )
        sent_count = message.send(fail_silently=False)
        if sent_count != 1:
            raise RuntimeError("The email service did not confirm delivery.")
    except Exception as error:
        submission.acknowledgement_email_status = (
            AcknowledgementEmailStatus.FAILED
        )
        submission.acknowledgement_email_error = str(error)[:2000]
        submission.save(
            update_fields=(
                "acknowledgement_email_status",
                "acknowledgement_email_error",
                "updated_at",
            )
        )
        return

    submission.acknowledgement_email_status = AcknowledgementEmailStatus.SENT
    submission.acknowledgement_email_sent_at = timezone.now()
    submission.acknowledgement_email_error = ""
    submission.save(
        update_fields=(
            "acknowledgement_email_status",
            "acknowledgement_email_sent_at",
            "acknowledgement_email_error",
            "updated_at",
        )
    )

