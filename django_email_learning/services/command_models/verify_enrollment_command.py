from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import (
    Enrollment,
    EnrollmentStatus,
    NewsletterSubscriber,
)
from pydantic import Field

from django_email_learning.services.command_models.exceptions.invalid_enrollment_error import (
    InvalidEnrollmentError,
)
from django_email_learning.services.command_models.exceptions.invalid_verification_code_error import (
    InvalidVerificationCodeError,
)
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _
from typing import Literal


class VerifyEnrollmentCommand(AbstractCommand):
    command_name: Literal["verify_enrollment"] = "verify_enrollment"
    enrollment_id: int = Field(..., gt=0)
    verification_code: str = Field(..., pattern=r"^\d{6}$")

    def execute(self) -> None:
        try:
            enrollment = Enrollment.objects.get(
                id=self.enrollment_id, status=EnrollmentStatus.UNVERIFIED
            )
        except Enrollment.DoesNotExist:
            self.logger.error(
                f"Verification Failed: No unverified enrollment found with ID {self.enrollment_id}"
            )
            # Check if enrollment exists but is not unverified
            if Enrollment.objects.filter(id=self.enrollment_id).exists():
                return
            raise InvalidEnrollmentError(
                f"No unverified enrollment found with ID {self.enrollment_id}"
            )

        if str(enrollment.activation_code) != str(self.verification_code):
            self.logger.error(
                f"Verification Failed: Invalid verification code for Enrollment ID {self.enrollment_id}"
            )
            raise InvalidVerificationCodeError(
                f"Invalid verification code for Enrollment ID {self.enrollment_id}"
            )

        enrollment.status = EnrollmentStatus.ACTIVE
        enrollment.activation_code = None
        enrollment.save()
        self.logger.info(
            f"Enrollment Verified: Enrollment ID {self.enrollment_id} has been activated"
        )

        enrollment.schedule_first_content_delivery()
        self.logger.info(
            f"Content Delivery Scheduled: First content delivery scheduled for Enrollment ID {self.enrollment_id}"
        )
        metric_service.user_enrollment_activated(
            enrollment.course.slug, enrollment.course.organization.id
        )

        # Auto-subscribe to linked newsletter (idempotent)
        newsletter = enrollment.course.newsletter
        newsletter_subscriber = None
        if newsletter:
            (
                newsletter_subscriber,
                _created,
            ) = NewsletterSubscriber.objects.get_or_create(
                newsletter=newsletter,
                email=enrollment.learner.email,
            )

        # Send confirmation email
        subject = _("Enrollment Verified")
        course_image_url = None
        if enrollment.course.image:
            image_url = enrollment.course.image.url
            if image_url.startswith(("http://", "https://")):
                course_image_url = image_url
            else:
                site_base_url = settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]
                course_image_url = f"{site_base_url}".rstrip("/") + image_url

        newsletter_unsubscribe_url = None
        if newsletter_subscriber:
            site_base_url = str(settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]).rstrip(
                "/"
            )
            unsubscribe_path = reverse(
                "django_email_learning:public:newsletter_unsubscribe",
                kwargs={"token": newsletter_subscriber.unsubscribe_token},
            )
            newsletter_unsubscribe_url = f"{site_base_url}{unsubscribe_path}"

        email_ctx = {
            "course_title": enrollment.course.title,
            "organization_name": enrollment.course.organization.name,
        }
        if newsletter_unsubscribe_url:
            email_ctx["newsletter_title"] = newsletter.title  # type: ignore[union-attr]
            email_ctx["newsletter_unsubscribe_url"] = newsletter_unsubscribe_url

        body = render_to_string("emails/enrollment_verified.txt", email_ctx)

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_sender_service.from_email,
            to=[enrollment.learner.email],
        )
        html_content = render_to_string(
            "emails/enrollment_verified.html",
            {**email_ctx, "course_image_url": course_image_url},
        )
        email.attach_alternative(html_content, "text/html")

        email_sender_service.send(email=email)
