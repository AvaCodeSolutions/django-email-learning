from typing import Any

from django.conf import settings
from django.conf.global_settings import LANGUAGES
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from PIL import Image

from django_email_learning.models.imap_connections import ImapConnection
from django_email_learning.models.newsletters import Newsletter
from django_email_learning.services import jwt_service

from .enums.enrollment_status import EnrollmentStatus
from .enums.from_email_type import FromEmailType
from .organizations import Organization, OrganizationUser, domain_wide_email_enabled


class Course(models.Model):
    title = models.CharField(max_length=200)
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
    send_certificate = models.BooleanField(default=True)
    from_email_type = models.CharField(
        max_length=32,
        choices=[(t.value, t.name.replace("_", " ").title()) for t in FromEmailType],
        default=FromEmailType.PLATFORM_DEFAULT.value,
        help_text="Which address course content emails are sent from.",
    )

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
    def enrollments_count(self) -> dict[str, int]:
        qs = self.enrollments.aggregate(
            unverified=models.Count("id", filter=models.Q(status=EnrollmentStatus.UNVERIFIED)),
            active=models.Count("id", filter=models.Q(status=EnrollmentStatus.ACTIVE)),
            completed=models.Count("id", filter=models.Q(status=EnrollmentStatus.COMPLETED)),
            deactivated=models.Count("id", filter=models.Q(status=EnrollmentStatus.DEACTIVATED)),
            total=models.Count("id"),
        )
        return qs

    @property
    def public_url(self) -> str | None:
        if not (self.enabled and self.is_public and self.organization.is_public):
            return None
        path = reverse(
            "django_email_learning:public:course_view",
            kwargs={"organization_id": self.organization.id, "course_slug": self.slug},
        )
        return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{path}"

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
