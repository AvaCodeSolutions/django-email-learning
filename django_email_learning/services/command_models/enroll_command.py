from typing import Literal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from django_email_learning.models import (
    BlockedEmail,
    Course,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Organization,
)
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email


class EnrollCommand(AbstractCommand):
    command_name: Literal["enroll"] = "enroll"
    email: str
    course_slug: str
    organization_id: int
    no_verification: bool = False
    case_insensitive_course_slug: bool = False

    def execute(self) -> None:
        # Check if the email is blocked
        if BlockedEmail.objects.filter(email=self.email).exists():
            self.logger.info(f"Enrollment Rejected: {mask_email(self.email)} is blocked")
            raise BlockedEmailError(f"The email {mask_email(self.email)} is blocked.")

        # Enforce the organization's learner cap, but only for learners who
        # aren't already enrolled anywhere in the organization.
        is_new_learner = not Learner.objects.filter(email=self.email, organization_id=self.organization_id).exists()
        if is_new_learner:
            organization = Organization.objects.get(id=self.organization_id)
            if not organization.can_enroll_learner():
                self.logger.info(
                    f"Enrollment Rejected: organization {self.organization_id} has reached its learner cap"
                )
                raise LearnerCapExceededError(
                    f"Organization {self.organization_id} has reached its maximum number of learners."
                )

        # Check if Learner with the email exists, if not create one
        learner, created = Learner.objects.get_or_create(email=self.email, organization_id=self.organization_id)
        if created:
            self.logger.info(f"Created new Learner for email: {mask_email(self.email)}. Learner ID: {learner.id}")

        try:
            if self.case_insensitive_course_slug:
                course = Course.objects.get(
                    slug__iexact=self.course_slug,
                    organization_id=self.organization_id,
                    enabled=True,
                )
            else:
                course = Course.objects.get(
                    slug=self.course_slug,
                    organization_id=self.organization_id,
                    enabled=True,
                )
        except Course.DoesNotExist:
            self.logger.error(
                f"Enrollment Failed: Invalid course slug '{self.course_slug}'"
                f" for organization ID {self.organization_id}"
            )
            raise InvalidCourseSlugError(
                f"Course with slug '{self.course_slug}' does not exist or is not enabled"
                f" for organization ID {self.organization_id}"
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
        enrollment = Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED)

        self.logger.info(
            f"Enrollment Successful: Learner ID {learner.id} enrolled in course '{self.course_slug}'."
            f" Enrollment ID: {enrollment.id}"
        )

        metric_service.user_enrolled_in_course(self.course_slug, self.organization_id)

        if self.no_verification:
            self.logger.info(f"Verification email skipped for Enrollment ID: {enrollment.id} as per command parameter")
            return

        # Send verification email

        token = jwt_service.generate_jwt(
            {
                "verification_code": enrollment.activation_code,
                "enrollment_id": enrollment.id,
            }
        )

        verification_relative_path = reverse("django_email_learning:personalised:verify_enrollment") + f"?token={token}"
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
        verification_link = DJANGO_EMAIL_LEARNING_SETTINGS["SITE_BASE_URL"] + verification_relative_path

        template_context = {
            "course_title": course.title,
            "verification_link": verification_link,
            "verification_code": enrollment.activation_code,
            "organization_name": course.organization.name,
            "support_imap_interface": course.imap_connection is not None,
            "imap_email_address": course.imap_connection.email if course.imap_connection else None,
            **email_sender_service.organization_footer_context(course),
        }
        subject = _("Verify your enrollment")
        body = render_to_string(
            "emails/enrollment_verification.txt",
            template_context,
        )

        to_emails = [self.email]

        html_content = render_to_string(
            "emails/enrollment_verification.html",
            template_context,
        )

        # TODO: Add AMP content/type to activate directly in email clients that support it

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_sender_service.from_email_for_course(course),
            to=to_emails,
        )
        email.attach_alternative(html_content, "text/html")
        email_sender_service.send(email)

        self.logger.info(f"Verification email sent to {mask_email(self.email)} for Enrollment ID: {enrollment.id}")
