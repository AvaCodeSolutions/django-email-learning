import base64
import uuid
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.module_loading import import_string

from .enums.enrollment_status import EnrollmentStatus

User = get_user_model()


class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    logo = models.ImageField(upload_to="organization_logos/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    embed_token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def generate_embed_token() -> str:
        """Generates an opaque, publishable identifier for the embeddable enroll/
        newsletter-subscribe API (see EMBEDDABLE_ENROLLMENT_ENABLED).

        Unlike ApiKey.key, this is not a secret - it's designed to sit in a
        third-party site's public page source - so it's stored unencrypted and
        looked up by direct equality rather than decrypted per-row.
        """
        return base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode().rstrip("=")

    @property
    def public_url(self) -> str | None:
        if not self.is_public:
            return None
        path = reverse(
            "django_email_learning:public:organization_view",
            kwargs={"organization_id": self.id},
        )
        return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{path}"

    def get_learners_cap(self) -> int:
        """
        Returns the maximum number of learners allowed for this organization.
        0 means unlimited.

        Reads DJANGO_EMAIL_LEARNING["LEARNERS"]["MAX_LEARNERS_PER_ORGANIZATION"] by
        default. If DJANGO_EMAIL_LEARNING["LEARNERS"]["LEARNERS_CAP_RESOLVER"] is set
        to a dotted path to a callable(organization: Organization) -> int, that
        callable is used instead, letting library users implement custom per-organization
        logic (e.g. tiered plans).
        """
        learners_settings: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("LEARNERS", {})
        resolver_path = learners_settings.get("LEARNERS_CAP_RESOLVER")
        if resolver_path:
            resolver = import_string(resolver_path)
            return resolver(self)
        return learners_settings.get("MAX_LEARNERS_PER_ORGANIZATION", 0)

    def can_enroll_learner(self) -> bool:
        cap = self.get_learners_cap()
        if not cap:
            return True
        active_learner_count = self.learner_set.filter(enrollments__status=EnrollmentStatus.ACTIVE).distinct().count()
        return active_learner_count < cap


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        WEBSITE = "website", "Website"
        YOUTUBE = "youtube", "YouTube"
        LINKEDIN = "linkedin", "LinkedIn"
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        TIKTOK = "tiktok", "TikTok"
        X = "x", "X (Twitter)"
        WHATSAPP = "whatsapp", "WhatsApp Channel"
        TELEGRAM = "telegram", "Telegram Channel"
        SUBSTACK = "substack", "Substack"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="social_links")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    url = models.URLField(max_length=500)

    class Meta:
        ordering = ["platform"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "platform"], name="unique_organization_platform")
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} - {self.platform}"


class OrganizationUser(models.Model):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        INSTRUCTOR = "instructor", "Instructor"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(
        max_length=50,
        choices=Roles.choices,
        db_index=True,
    )
    display_name = models.CharField(max_length=200, null=True, blank=True)
    photo = models.ImageField(upload_to="org_user_photos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.organization.name}"

    def can_act_as_instructor(self) -> bool:
        if self.role == OrganizationUser.Roles.INSTRUCTOR and self.display_name:
            return True
        if self.role == OrganizationUser.Roles.ADMIN and self.display_name:
            return True
        return False

    def clean(self) -> None:
        super().clean()
        if self.role == OrganizationUser.Roles.INSTRUCTOR and not self.display_name:
            raise ValidationError("Instructor role requires a display name.")

    def save(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "organization"], name="unique_user_organization")]
