import uuid

from django.db import models


class DonationType(models.TextChoices):
    CASH = "cash", "Cash"
    GOODS = "goods", "Goods"


class AcknowledgementEmailStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class DonationSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone_number = models.CharField(max_length=40)
    donation_type = models.CharField(max_length=16, choices=DonationType.choices)
    details = models.TextField(max_length=2000)
    acknowledgement_email_status = models.CharField(
        max_length=16,
        choices=AcknowledgementEmailStatus.choices,
        default=AcknowledgementEmailStatus.PENDING,
    )
    acknowledgement_email_sent_at = models.DateTimeField(null=True, blank=True)
    acknowledgement_email_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "donation_submissions"
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(
                fields=("donation_type", "created_at"),
                name="donation_type_created_idx",
            ),
            models.Index(
                fields=("email", "created_at"),
                name="donation_email_created_idx",
            ),
        )

    def clean(self) -> None:
        super().clean()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.email = self.email.strip().lower()
        self.phone_number = self.phone_number.strip()
        self.details = self.details.strip()

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        self.email = self.email.strip().lower()
        self.phone_number = self.phone_number.strip()
        self.details = self.details.strip()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.first_name} {self.last_name} - "
            f"{self.get_donation_type_display()}"
        )

