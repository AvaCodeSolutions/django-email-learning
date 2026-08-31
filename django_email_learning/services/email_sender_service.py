from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from django_email_learning.models import Course, Organization


class EmailSenderService:
    def __init__(self) -> None:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
        try:
            configured_email_sender = import_string(DJANGO_EMAIL_LEARNING_SETTINGS["EMAIL_SENDER"])
            self.email_sender = (
                configured_email_sender() if isinstance(configured_email_sender, type) else configured_email_sender
            )
        except KeyError:
            from django_email_learning.services.defaults.email_sender import (
                DjangoEmailSender,
            )

            self.email_sender = DjangoEmailSender()

        try:
            self.from_email = DJANGO_EMAIL_LEARNING_SETTINGS["FROM_EMAIL"]
        except (AttributeError, KeyError):
            try:
                self.from_email = settings.DEFAULT_FROM_EMAIL
            except AttributeError:
                self.from_email = ""
        if not self.from_email:
            raise ValueError("Either set DJANGO_EMAIL_LEARNING['FROM_EMAIL'] or DEFAULT_FROM_EMAIL.")

    def from_email_for_organization(self, organization: "Organization", *, fallback: str | None = None) -> str:
        """The organization's shared-domain 'From' address when domain-wide email
        is enabled, otherwise ``fallback`` (defaulting to the platform ``FROM_EMAIL``).
        """
        from django_email_learning.models.organizations import domain_wide_email_enabled

        if domain_wide_email_enabled() and organization.domain_wide_from_email:
            return organization.domain_wide_from_email
        return fallback if fallback is not None else self.from_email

    def from_email_for_course(self, course: "Course") -> str:
        """Resolve the 'From' address for a course's content emails.

        Returns the organization's domain-wide address only when the course opted
        in AND the installation still has domain-wide email enabled; otherwise
        falls back to the platform default. The stored course value is never
        mutated, so re-enabling the setting restores the organization address.
        """
        from django_email_learning.models.courses import FromEmailType

        if course.from_email_type == FromEmailType.ORGANIZATION:
            return self.from_email_for_organization(course.organization)
        return self.from_email

    def _absolute_url(self, url: str) -> str:
        """Make a possibly-relative media/static URL absolute for use in email,
        prefixing ``SITE_BASE_URL`` unless the storage already returns an
        absolute URL (e.g. S3)."""
        if url.startswith(("http://", "https://", "//")):
            return url
        site_base_url = str(settings.DJANGO_EMAIL_LEARNING.get("SITE_BASE_URL", "")).rstrip("/")
        return f"{site_base_url}{url}"

    def organization_footer_context(self, course: "Course") -> dict:
        """Template context for the optional organization footer on a course's
        HTML emails. When ``course.show_organization_footer`` is off, only the
        ``org_footer_enabled`` flag is meaningful and nothing else is loaded.
        """
        organization = course.organization
        enabled = course.show_organization_footer
        return {
            "org_footer_enabled": enabled,
            "org_footer_name": organization.name,
            "org_footer_logo_url": self._absolute_url(organization.logo.url) if enabled and organization.logo else None,
            "org_footer_social_links": list(organization.social_links.all()) if enabled else [],
        }

    def send(self, email: EmailMultiAlternatives) -> None:
        self.email_sender.send_email(email)


email_sender_service = EmailSenderService()
