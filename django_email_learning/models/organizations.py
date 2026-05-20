from typing import Any

from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    logo = models.ImageField(upload_to="organization_logos/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    website = models.URLField(max_length=500, null=True, blank=True)
    youtube_channel = models.URLField(max_length=500, null=True, blank=True)
    linkedin_page = models.URLField(max_length=500, null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self) -> str:
        return self.name

    @property
    def public_url(self) -> str | None:
        if not self.is_public:
            return None
        path = reverse(
            "django_email_learning:public:organization_view",
            kwargs={"organization_id": self.id},
        )
        return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{path}"


class OrganizationUser(models.Model):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        INSTRUCTOR = "instructor", "Instructor"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
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
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="unique_user_organization"
            )
        ]
