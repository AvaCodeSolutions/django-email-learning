from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import Enrollment, EnrollmentStatus
from pydantic import Field

from django_email_learning.services.command_models.exceptions.invalid_enrollment_error import (
    InvalidEnrollmentError,
)
from django_email_learning.services.command_models.exceptions.invalid_verification_code_error import (
    InvalidVerificationCodeError,
)
from django_email_learning.services.email_sender_service import EmailSenderService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
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

        # Send confirmation email
        email_service = EmailSenderService()
        subject = _("Enrollment Verified")
        body = render_to_string(
            "emails/enrollment_verified.txt",
            {
                "course_title": enrollment.course.title,
                "organization_name": enrollment.course.organization.name,
            },
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_service.from_email,
            to=[enrollment.learner.email],
        )
        html_content = render_to_string(
            "emails/enrollment_verified.html",
            {
                "course_title": enrollment.course.title,
                "organization_name": enrollment.course.organization.name,
            },
        )
        email.attach_alternative(html_content, "text/html")

        email_service.send(email=email)
