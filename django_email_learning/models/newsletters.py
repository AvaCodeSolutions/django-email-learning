import uuid

from django.conf.global_settings import LANGUAGES
from django.db import models

from .organizations import Organization


class Newsletter(models.Model):
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=10, choices=LANGUAGES, default="en")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="newsletters"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.organization.name})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["title", "organization"], name="unique_newsletter_title_per_org"
            )
        ]


class NewsletterSubscriber(models.Model):
    newsletter = models.ForeignKey(
        Newsletter, on_delete=models.CASCADE, related_name="subscribers"
    )
    email = models.EmailField(max_length=254)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribe_token = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False
    )

    def __str__(self) -> str:
        return f"{self.email} → {self.newsletter.title}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["newsletter", "email"], name="unique_subscriber_per_newsletter"
            )
        ]


class Sendout(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"

    newsletter = models.ForeignKey(
        Newsletter, on_delete=models.CASCADE, related_name="sendouts"
    )
    subject = models.CharField(max_length=500)
    body = models.TextField()
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.subject} — {self.newsletter.title} ({self.status})"


class SendoutDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    sendout = models.ForeignKey(
        Sendout, on_delete=models.CASCADE, related_name="deliveries"
    )
    subscriber = models.ForeignKey(
        NewsletterSubscriber,
        on_delete=models.CASCADE,
        related_name="sendout_deliveries",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sendout", "subscriber"],
                name="unique_sendout_delivery_per_subscriber",
            )
        ]

    def __str__(self) -> str:
        return f"{self.sendout.subject} → {self.subscriber.email} ({self.status})"
