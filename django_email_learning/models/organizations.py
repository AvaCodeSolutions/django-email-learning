import base64
import uuid
from email.utils import formataddr
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.text import slugify

from .enums.enrollment_status import EnrollmentStatus
from .validators import MAX_ORGANIZATION_NAME_LENGTH, validate_organization_name

User = get_user_model()

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a valid hex color, e.g. #4A5EC0.",
)


def domain_wide_email_enabled() -> bool:
    """True when the installation has authorized this platform's mail service to
    send from any address at a shared domain (see DJANGO_EMAIL_LEARNING
    ["DOMAIN_WIDE_EMAIL"]). Both ENABLED and a non-empty DOMAIN are required.

    This single switch gates the organization-addressed sender for both course
    content emails (per-course opt-in via Course.from_email_type) and newsletter
    sendouts.
    """
    conf = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DOMAIN_WIDE_EMAIL", {})
    return bool(conf.get("ENABLED") and conf.get("DOMAIN"))


class Organization(models.Model):
    name = models.CharField(max_length=MAX_ORGANIZATION_NAME_LENGTH, validators=[validate_organization_name])
    logo = models.ImageField(upload_to="organization_logos/", null=True, blank=True)
    description = models.TextField(null=True, blank=True, validators=[MaxLengthValidator(1000)])
    is_public = models.BooleanField(default=True)
    brand_color = models.CharField(max_length=7, default="#4A5EC0", validators=[hex_color_validator])
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    embed_token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)

    def __str__(self) -> str:
        # Names are not unique, so the id disambiguates same-named organizations
        # wherever a human has to pick one (e.g. admin foreign key dropdowns).
        return f"{self.name} (#{self.pk})"

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_embed_token() -> str:
        """Generates an opaque, publishable identifier for the embeddable enroll/
        newsletter-subscribe API (see EMBEDDABLE_ENROLLMENT_ENABLED).

        Unlike ApiKey.key, this is not a secret - it's designed to sit in a
        third-party site's public page source - so it's stored unencrypted and
        looked up by direct equality rather than decrypted per-row.
        """
        return base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes).decode().rstrip("=")

    def get_or_create_embed_token(self) -> str:
        """Returns the organization's embed_token, generating and persisting one
        on first use so features built on it (e.g. the course embed snippet)
        work without requiring an admin to run generate_embed_token first.
        """
        if not self.embed_token:
            self.embed_token = self.generate_embed_token()
            self.save(update_fields=["embed_token"])
        return self.embed_token

    @property
    def email_local_part(self) -> str:
        """Local part for this organization's domain-wide sending address. The id
        keeps it unique since organization names are not (see __str__).
        """
        slug = slugify(self.name)
        return f"{slug}-{self.id}" if slug else f"org-{self.id}"

    @property
    def domain_wide_from_email(self) -> str:
        """The ``From`` header for this organization under a shared sending domain:
        ``<Organization Name> <org-slug-id@domain>``. Returns "" when no
        ``DOMAIN_WIDE_EMAIL["DOMAIN"]`` is configured. Callers that must also
        honour the ENABLED switch should guard with ``domain_wide_email_enabled()``.
        """
        domain = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DOMAIN_WIDE_EMAIL", {}).get("DOMAIN")
        if not domain:
            return ""
        return formataddr((self.name, f"{self.email_local_part}@{domain}"))

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
