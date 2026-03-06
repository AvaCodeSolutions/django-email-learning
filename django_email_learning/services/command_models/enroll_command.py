from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.models import (
    BlockedEmail,
    Learner,
    Enrollment,
    Course,
    EnrollmentStatus,
)
from django_email_learning.services.utils import mask_email
from django_email_learning.services.email_sender_service import EmailSenderService
from django_email_learning.services import jwt_service
from django_email_learning.services.metrics_service import MetricsService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.conf import settings
from django.urls import reverse
from typing import Literal


class EnrollCommand(AbstractCommand):
    command_name: Literal["enroll"] = "enroll"
    email: str
    course_slug: str
    organization_id: int
    no_verification: bool = False

    def execute(self) -> None:
        metric_service = MetricsService()
        # Check if the email is blocked
        if BlockedEmail.objects.filter(email=self.email).exists():
            self.logger.info(
                f"Enrollment Rejected: {mask_email(self.email)} is blocked"
            )
            raise BlockedEmailError(f"The email {mask_email(self.email)} is blocked.")

        # Check if Learner with the email exists, if not create one
        learner, created = Learner.objects.get_or_create(
            email=self.email, organization_id=self.organization_id
        )
        if created:
            self.logger.info(
                f"Created new Learner for email: {mask_email(self.email)}. Learner ID: {learner.id}"
            )

        try:
            course = Course.objects.get(
                slug=self.course_slug,
                organization_id=self.organization_id,
                enabled=True,
            )
        except Course.DoesNotExist:
            self.logger.error(
                f"Enrollment Failed: Invalid course slug '{self.course_slug}' for organization ID {self.organization_id}"
            )
            raise InvalidCourseSlugError(
                f"Course with slug '{self.course_slug}' does not exist or is not enabled for organization ID {self.organization_id}"
            )

        # Check if an enrollment already exists
        if (
            Enrollment.objects.filter(learner=learner, course=course)
            .exclude(status=EnrollmentStatus.DEACTIVATED)
            .exists()
        ):
            self.logger.info(
                f"Enrollment Skipped: Learner ID {learner.id} is already enrolled in course '{self.course_slug}'"
            )
            raise EnrollmentAlreadyExistsError(
                f"Learner with email {mask_email(self.email)} is already enrolled in course '{self.course_slug}'"
            )

        # Create the enrollment
        enrollment = Enrollment.objects.create(
            learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED
        )

        self.logger.info(
            f"Enrollment Successful: Learner ID {learner.id} enrolled in course '{self.course_slug}'. Enrollment ID: {enrollment.id}"
        )

        metric_service.user_enrolled_in_course(self.course_slug, self.organization_id)

        if self.no_verification:
            self.logger.info(
                f"Verification email skipped for Enrollment ID: {enrollment.id} as per command parameter"
            )
            return

        # Send verification email

        token = jwt_service.generate_jwt(
            {
                "verification_code": enrollment.activation_code,
                "enrollment_id": enrollment.id,
            }
        )

        verification_relative_path = (
            reverse("django_email_learning:personalised:verify_enrollment")
            + f"?token={token}"
        )
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        verification_link = (
            DJANGO_EMAIL_LEARNING_SETTINGS["SITE_BASE_URL"] + verification_relative_path
        )

        template_context = {
            "course_title": course.title,
            "verification_link": verification_link,
            "verification_code": enrollment.activation_code,
            "organization_name": course.organization.name,
            "support_imap_interface": course.imap_connection is not None,
            "imap_email_address": course.imap_connection.email
            if course.imap_connection
            else None,
        }
        email_service = EmailSenderService()
        subject = _("Verify your enrollment")
        body = render_to_string(
            "emails/enrolment_verification.txt",
            template_context,
        )

        to_emails = [self.email]

        html_content = render_to_string(
            "emails/enrolment_verification.html",
            template_context,
        )

        # TODO: Add AMP content/type to activate directly in email clients that support it

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_service.from_email,
            to=to_emails,
        )
        email.attach_alternative(html_content, "text/html")
        email_service.send(email)

        self.logger.info(
            f"Verification email sent to {mask_email(self.email)} for Enrollment ID: {enrollment.id}"
        )
