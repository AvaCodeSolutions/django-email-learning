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
