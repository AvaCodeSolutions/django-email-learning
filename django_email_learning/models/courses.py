from typing import Any
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import default_storage
from django.urls import reverse
from PIL import Image

from django_email_learning.models.imap_connections import ImapConnection
from .organizations import Organization, OrganizationUser
from .enums.enrollment_status import EnrollmentStatus
from django_email_learning.services import jwt_service
from django_email_learning.services.metrics_service import MetricsService
from django.conf.global_settings import LANGUAGES


METRIC_SERVICE = MetricsService()


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=50,
        help_text="A short label for the course, used in URLs or email interactive actions. You can not edit it later.",
    )
    description = models.TextField(null=True, blank=True)
    enabled = models.BooleanField(default=False)
    imap_connection = models.ForeignKey(
        ImapConnection, on_delete=models.SET_NULL, null=True, blank=True
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

    def __str__(self) -> str:
        return self.title

    class Meta:
        unique_together = [["slug", "organization"], ["title", "organization"]]

    def delete(
        self, using: Any | None = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        if self.enabled:
            raise ValueError(
                "Course can not be deleted when enabled, please disable the course first!"
            )
        return super().delete(using, keep_parents)

    @property
    def enrollments_count(self) -> dict[str, int]:
        unverified_count = self.enrollment_set.filter(
            status=EnrollmentStatus.UNVERIFIED
        ).count()
        active_count = self.enrollment_set.filter(
            status=EnrollmentStatus.ACTIVE
        ).count()
        completed_count = self.enrollment_set.filter(
            status=EnrollmentStatus.COMPLETED
        ).count()
        deactivated_count = self.enrollment_set.filter(
            status=EnrollmentStatus.DEACTIVATED
        ).count()
        total_count = self.enrollment_set.count()
        return {
            EnrollmentStatus.UNVERIFIED: unverified_count,
            EnrollmentStatus.ACTIVE: active_count,
            EnrollmentStatus.COMPLETED: completed_count,
            EnrollmentStatus.DEACTIVATED: deactivated_count,
            "total": total_count,
        }

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
                    raise ValueError(
                        "Image dimensions must be at least 580x360 pixels."
                    )
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
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="instructors"
    )
    org_user = models.ForeignKey(OrganizationUser, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.course.title} - {self.org_user.user.email}"

    def clean(self) -> None:
        super().clean()
        if self.org_user.organization != self.course.organization:
            raise ValidationError(
                "Instructor must belong to the same organization as the course."
            )
        if not self.org_user.can_act_as_instructor():
            raise ValidationError("Organization user doesn't have instructor role.")

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = [["course", "org_user"]]


class ExternalReference(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="external_references"
    )
    name = models.CharField(max_length=200)
    url = models.URLField(max_length=500)

    def __str__(self) -> str:
        return f"{self.course.title} - {self.name}"
