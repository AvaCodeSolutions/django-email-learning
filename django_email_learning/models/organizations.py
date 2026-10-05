import base64
import hashlib
import logging
import re
import uuid
from collections.abc import Callable, Iterable
from email.utils import formataddr
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import IntegrityError, models, transaction
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.text import slugify

from django_email_learning.services.favicon_service import is_raster_logo, make_favicon_png
from django_email_learning.services.public_urls import public_url_name

from .enums.enrollment_status import EnrollmentStatus
from .validators import MAX_ORGANIZATION_NAME_LENGTH, validate_organization_name

User = get_user_model()

logger = logging.getLogger(__name__)

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a valid hex color, e.g. #4A5EC0.",
)

ORGANIZATION_SLUG_MAX_LENGTH = 50

organization_slug_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    message="Use lowercase letters, numbers and single hyphens, e.g. acme-academy.",
)

# Slugs a new organization is never given, so no organization's public page can
# pass itself off as the platform's own. Replaced as a whole by
# DJANGO_EMAIL_LEARNING["RESERVED_ORGANIZATION_SLUGS"].
DEFAULT_RESERVED_ORGANIZATION_SLUGS = (
    "admin",
    "administrator",
    "api",
    "help",
    "official",
    "platform",
    "public",
    "staff",
    "support",
    "system",
)


def reserved_organization_slugs() -> frozenset[str]:
    conf = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return frozenset(conf.get("RESERVED_ORGANIZATION_SLUGS", DEFAULT_RESERVED_ORGANIZATION_SLUGS))


def generate_organization_slug(name: str, is_taken: Callable[[str], bool], reserved: Iterable[str]) -> str:
    """The slugified ``name``, or - when that is reserved or ``is_taken`` - the
    first free one of ``<slug>-2``, ``<slug>-3``, ... A name with nothing
    slugify keeps (one written entirely in a non-Latin script, say) becomes
    ``organization``. The base is cut short so the suffix always fits.
    """
    reserved = frozenset(reserved)
    # slugify keeps underscores and leaves runs of them and hyphens alone, but
    # organization_slug_validator allows only single hyphens between words.
    base = re.sub(r"[-_]+", "-", slugify(name)).strip("-") or "organization"
    candidate = base[:ORGANIZATION_SLUG_MAX_LENGTH].strip("-")
    counter = 1
    while candidate in reserved or is_taken(candidate):
        counter += 1
        suffix = f"-{counter}"
        candidate = f"{base[: ORGANIZATION_SLUG_MAX_LENGTH - len(suffix)].strip('-')}{suffix}"
    return candidate


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
    # A small square PNG rendered from the logo for the public pages' browser tab,
    # rebuilt whenever the logo changes. Empty while there is no logo, and for a
    # vector logo, which is served as its own favicon instead.
    favicon = models.ImageField(upload_to="organization_logos/", null=True, blank=True, editable=False)
    description = models.TextField(null=True, blank=True, validators=[MaxLengthValidator(1000)])
    is_public = models.BooleanField(default=True)
    brand_color = models.CharField(max_length=7, default="#4A5EC0", validators=[hex_color_validator])
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    embed_token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    # The public pages' address: /@<slug>/. Generated from the name when the
    # organization is created and kept from then on - renaming the organization
    # does not move its public pages, so links already shared keep working.
    slug = models.SlugField(
        max_length=ORGANIZATION_SLUG_MAX_LENGTH,
        unique=True,
        blank=True,
        validators=[organization_slug_validator],
        help_text="The organization's public address, /@<slug>/. Leave blank to generate it from the name. "
        "Changing it breaks links already shared to the old address.",
    )

    def __str__(self) -> str:
        # Names are not unique, so the id disambiguates same-named organizations
        # wherever a human has to pick one (e.g. admin foreign key dropdowns).
        return f"{self.name} (#{self.pk})"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # The logo as stored, to tell in save() whether it changed. Read from
        # __dict__ so a deferred logo is not fetched just for this; None marks
        # it as unknown, and a save then leaves the favicon alone.
        self._saved_logo_name: str | None
        if not self.pk:
            self._saved_logo_name = ""
        elif "logo" in self.__dict__:
            self._saved_logo_name = str(self.__dict__["logo"] or "")
        else:
            self._saved_logo_name = None

    # How many times save() regenerates a slug that another organization took
    # between generating it and inserting this one.
    SLUG_SAVE_ATTEMPTS = 3

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        slug_generated = not self.slug
        if slug_generated:
            self.slug = self._generate_slug()
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = {*kwargs["update_fields"], "slug"}
        self.full_clean()
        logo_changed = self._saved_logo_name is not None and (self.logo.name or "") != self._saved_logo_name
        if slug_generated:
            self._save_with_generated_slug(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
        if logo_changed:
            self.refresh_favicon()

    def _generate_slug(self) -> str:
        others = Organization.objects.exclude(pk=self.pk) if self.pk else Organization.objects.all()
        return generate_organization_slug(
            self.name,
            is_taken=lambda slug: others.filter(slug=slug).exists(),
            reserved=reserved_organization_slugs(),
        )

    def _save_with_generated_slug(self, *args: Any, **kwargs: Any) -> None:
        """full_clean() checked the slug was free, but another organization saved
        at the same moment can still take it before this one is inserted. The
        unique constraint catches that; generate the next free slug and retry.
        """
        for attempt in range(self.SLUG_SAVE_ATTEMPTS):
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return
            except IntegrityError:
                slug_taken = Organization.objects.filter(slug=self.slug).exclude(pk=self.pk).exists()
                if not slug_taken or attempt == self.SLUG_SAVE_ATTEMPTS - 1:
                    raise
                self.slug = self._generate_slug()

    def refresh_favicon(self) -> None:
        """Re-renders ``favicon`` from the current logo, or clears it when there is
        no raster logo to render. A logo Pillow cannot read leaves the organization
        without a favicon rather than failing the save that changed it.
        """
        if self.favicon.name:
            default_storage.delete(self.favicon.name)
        logo_name = self.logo.name or ""
        favicon_name = ""
        if logo_name and is_raster_logo(logo_name):
            try:
                with default_storage.open(logo_name) as logo_file:
                    png = make_favicon_png(logo_file)
                # Named by content: media is typically served with a long cache
                # lifetime, so a new favicon needs a new URL to reach browsers.
                digest = hashlib.sha256(png).hexdigest()[:12]
                favicon_name = default_storage.save(
                    f"organization_logos/{self.pk}/favicon-{digest}.png", ContentFile(png)
                )
            except Exception:
                logger.warning("Could not render a favicon for organization %s", self.pk, exc_info=True)
        self.favicon = favicon_name or None
        Organization.objects.filter(pk=self.pk).update(favicon=favicon_name or None)
        self._saved_logo_name = logo_name

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

    def get_public_path(self) -> str:
        """The path of the organization's public page, whether or not the page is
        currently public. See DJANGO_EMAIL_LEARNING["PUBLIC_URL_NAMES"].
        """
        return reverse(public_url_name("organization"), kwargs={"organization_slug": self.slug})

    @property
    def public_url(self) -> str | None:
        if not self.is_public:
            return None
        return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{self.get_public_path()}"

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
