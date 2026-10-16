from typing import Any

from django.conf import settings
from django.conf.global_settings import LANGUAGES
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import MaxLengthValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from PIL import Image

from django_email_learning.models.imap_connections import ImapConnection
from django_email_learning.models.newsletters import Newsletter
from django_email_learning.services import jwt_service
from django_email_learning.services.public_urls import public_url_name

from .enums.enrollment_confirmation import EnrollmentConfirmation
from .enums.enrollment_status import EnrollmentStatus
from .enums.from_email_type import FromEmailType
from .organizations import Organization, OrganizationUser, domain_wide_email_enabled
from .validators import validate_safe_name

MAX_CERTIFICATE_FIELDS = 4


class Course(models.Model):
    title = models.CharField(max_length=200, validators=[validate_safe_name])
    slug = models.SlugField(
        max_length=50,
        help_text="A short label for the course, used in URLs or email interactive actions. You can not edit it later.",
    )
    description = models.TextField(null=True, blank=True, validators=[MaxLengthValidator(1000)])
    enabled = models.BooleanField(default=False)
    imap_connection = models.ForeignKey(ImapConnection, on_delete=models.SET_NULL, null=True, blank=True)
    newsletter = models.ForeignKey(
        Newsletter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="course_images/", null=True, blank=True)
    language = models.CharField(
        max_length=10,
        choices=LANGUAGES,
        default="en",
    )
    target_audience = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    # An optional price, shown on the public course page. Nothing here charges learners;
    # taking payment is up to the organization, typically behind an enrollment or content gate.
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Shown on the public course page. Leave empty to show no price.",
    )
    price_currency = models.CharField(
        max_length=3,
        blank=True,
        default="",
        validators=[RegexValidator(r"^[A-Z]{3}$", "Use a three-letter ISO 4217 currency code, such as USD.")],
        help_text="ISO 4217 code of the price's currency, such as USD or EUR.",
    )
    price_subtitle = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Shown under the price, to tell learners what it covers or when it applies.",
    )
    send_certificate = models.BooleanField(default=True)
    from_email_type = models.CharField(
        max_length=32,
        choices=[(t.value, t.name.replace("_", " ").title()) for t in FromEmailType],
        default=FromEmailType.PLATFORM_DEFAULT.value,
        help_text="Which address course content emails are sent from.",
    )
    show_organization_footer = models.BooleanField(
        default=False,
        help_text="Show the organization name and social links in the footer of this course's emails.",
    )
    enrollment_confirmation = models.CharField(
        max_length=20,
        choices=[
            (EnrollmentConfirmation.LINK.value, "Email link"),
            (EnrollmentConfirmation.GATE.value, "Enrollment gate"),
        ],
        default=EnrollmentConfirmation.LINK.value,
        help_text="Whether learners confirm their own enrollment, or an outside system does through the API.",
    )
    enrollment_gate_key = models.SlugField(
        max_length=100,
        blank=True,
        default="",
        help_text="Names the enrollment gate in the unlock API. Required when enrollments are gated.",
    )
    # The emails below are rich text with {{ course_title }} and {{ organization_name }}
    # placeholders; null sends the built-in default. See services/enrollment_emails.py.
    enrollment_email_subject = models.CharField(max_length=200, null=True, blank=True)
    enrollment_email_body = models.TextField(
        null=True,
        blank=True,
        help_text="Sent on enrollment when enrollments are gated, in place of the verification email.",
    )
    enrollment_reminder_enabled = models.BooleanField(
        default=False,
        help_text="Remind learners of gated enrollments still unconfirmed. Link-confirmed courses always do.",
    )
    enrollment_reminder_subject = models.CharField(max_length=200, null=True, blank=True)
    enrollment_reminder_body = models.TextField(null=True, blank=True)
    welcome_email_subject = models.CharField(max_length=200, null=True, blank=True)
    welcome_email_body = models.TextField(
        null=True,
        blank=True,
        help_text="Sent once an enrollment is confirmed.",
    )

    def has_branching(self) -> bool:
        """Whether any content in this course routes a learner onto a track.

        A track nothing routes onto is unreachable, so a course holding one mid-authoring
        is still a straight line and its learners still get a progress percentage.
        """
        return self.coursecontent_set.filter(transitions__isnull=False).exists()

    def validate_branching(self) -> None:
        """Re-check where every track and routing rule in this course leads, raising the first violation.

        Those checks compare against other rows - where a merge point sits relative to its
        branch point, which track a content is on. Reordering or moving content changes those
        rows without saving the track or the rule that depends on them, so a structural edit
        calls this before committing. Checks on a single row's own fields run when it is saved.
        """
        # The graph reads the course models, so a module-level import would cycle.
        from django_email_learning.services.course_graph import CourseGraph

        CourseGraph(self.id).validate()

    def __str__(self) -> str:
        return self.title

    class Meta:
        unique_together = [["slug", "organization"], ["title", "organization"]]

    def clean(self) -> None:
        super().clean()
        if self.from_email_type == FromEmailType.ORGANIZATION and not domain_wide_email_enabled():
            previous = (
                Course.objects.filter(pk=self.pk).values_list("from_email_type", flat=True).first() if self.pk else None
            )
            if previous != FromEmailType.ORGANIZATION:
                raise ValidationError({"from_email_type": "Domain-wide email is not enabled for this installation."})
        if self.price is not None and not self.price_currency:
            raise ValidationError({"price_currency": "A price needs a currency."})
        if self.price is None and self.price_subtitle:
            raise ValidationError({"price_subtitle": "A price subtitle needs a price."})
        if self.is_enrollment_gated:
            if not self.enrollment_gate_key:
                raise ValidationError({"enrollment_gate_key": "An enrollment gate needs a key."})
            # Content gates and the enrollment gate share the unlock API, so their keys
            # must not name the same thing.
            if self.pk and self.coursecontent_set.filter(gate__key=self.enrollment_gate_key).exists():
                raise ValidationError(
                    {
                        "enrollment_gate_key": "A gate in this course already uses the key '%(key)s'."
                        % {"key": self.enrollment_gate_key}
                    }
                )

    @property
    def is_enrollment_gated(self) -> bool:
        return self.enrollment_confirmation == EnrollmentConfirmation.GATE

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def organization_from_email(self) -> str:
        """The 'From' header this course would use under the organization option:
        "<Org Name> <org-slug-id@domain>". Returns "" when no domain is configured.
        """
        return self.organization.domain_wide_from_email

    def delete(self, using: Any | None = None, keep_parents: bool = False) -> tuple[int, dict[str, int]]:
        if self.enabled:
            raise ValueError("Course can not be deleted when enabled, please disable the course first!")
        return super().delete(using, keep_parents)

    @property
    def has_published_content(self) -> bool:
        """Whether a new enrollment has published content to start on. Enrollments
        always start on the main spine, so content published only inside a track
        does not count.
        """
        return self.coursecontent_set.filter(track__isnull=True, is_published=True).exists()

    def disable_if_no_published_content(self) -> bool:
        """Disable the course once it has nothing left to start learners on.
        Returns whether the course was disabled by this call.
        """
        if not self.enabled or self.has_published_content:
            return False
        self.enabled = False
        self.save(update_fields=["enabled"])
        return True

    @property
    def enrollments_count(self) -> dict[str, int]:
        qs = self.enrollments.aggregate(
            unverified=models.Count("id", filter=models.Q(status=EnrollmentStatus.UNVERIFIED)),
            active=models.Count("id", filter=models.Q(status=EnrollmentStatus.ACTIVE)),
            completed=models.Count("id", filter=models.Q(status=EnrollmentStatus.COMPLETED)),
            deactivated=models.Count("id", filter=models.Q(status=EnrollmentStatus.DEACTIVATED)),
            total=models.Count("id"),
        )
        return qs

    def get_public_path(self) -> str:
        """The path of the course's public page, whether or not the page is
        currently public. See DJANGO_EMAIL_LEARNING["PUBLIC_URL_NAMES"].
        """
        return reverse(
            public_url_name("course"),
            kwargs={"organization_slug": self.organization.slug, "course_slug": self.slug},
        )

    @property
    def public_url(self) -> str | None:
        if not (self.enabled and self.is_public and self.organization.is_public):
            return None
        return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{self.get_public_path()}"

    def generate_unsubscribe_link(self, email: str) -> str:
        payload = {
            "email": email,
            "course_slug": self.slug,
            "organization_id": self.organization.id,
        }
        token = jwt_service.generate_jwt(payload=payload)
        unsubscribe_path = reverse("django_email_learning:personalised:unsubscribe")
        link = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{unsubscribe_path}?token={token}"
        return link

    def replace_image(self, file_path: str) -> str:
        if default_storage.exists(file_path):
            with default_storage.open(file_path) as f:
                img = Image.open(f)
                width, height = img.size
                if width < 580 or height < 360:
                    raise ValueError("Image dimensions must be at least 580x360 pixels.")
            allowed_extensions = [".jpg", ".jpeg", ".png", ".svg"]
            if not any(file_path.lower().endswith(ext) for ext in allowed_extensions):
                raise ValueError("Image must be an image file with a valid extension.")
            final_path = f"organization/{self.organization.id}/course_images/{self.id}_{file_path.split('/')[-1]}"
            default_storage.save(final_path, default_storage.open(file_path))
            self.image = final_path
            self.save()
            return final_path
        else:
            raise ValueError("Image file does not exist.")


class CertificateField(models.Model):
    """A label/value pair the course prints on every certificate it issues, e.g. "CPD Points"/"5".

    A course holds at most ``MAX_CERTIFICATE_FIELDS`` of them. They are copied onto each
    certificate as it is issued, so editing or removing one here never changes a certificate
    that is already out.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificate_fields")
    label = models.CharField(max_length=50, validators=[validate_safe_name])
    value = models.CharField(max_length=100, validators=[validate_safe_name])
    order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.course.title} - {self.label}"

    def save(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)


class CourseInstructor(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="instructors")
    org_user = models.ForeignKey(OrganizationUser, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.course.title} - {self.org_user.user.email}"

    def clean(self) -> None:
        super().clean()
        if self.org_user.organization != self.course.organization:
            raise ValidationError("Instructor must belong to the same organization as the course.")
        if not self.org_user.can_act_as_instructor():
            raise ValidationError("Organization user doesn't have instructor role.")

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = [["course", "org_user"]]


class ExternalReference(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="external_references")
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500)

    def __str__(self) -> str:
        return f"{self.course.title} - {self.name}"
