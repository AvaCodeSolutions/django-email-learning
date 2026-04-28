from django_email_learning.models import (
    ContentDelivery,
    DeactivationReason,
    EnrollmentStatus,
    JobExecution,
    JobName,
    JobStatus,
    Quiz,
)
from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.services.metrics_service import MetricsService
from django_email_learning.services.email_sender_service import EmailSenderService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils import timezone
import logging

from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)
metric_service = MetricsService()


class DeactivateInactiveEnrollmentsJob:
    def run(self) -> None:
        if JobExecution.objects.filter(
            job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
            status=JobStatus.RUNNING.value,
        ).exists():
            logger.warning(
                "Another instance of DEACTIVATE_ENROLLMENTS is already running. Exiting this run."
            )
            return

        job_execution = JobExecution.objects.create(
            job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
            status=JobStatus.RUNNING.value,
            started_at=timezone.now(),
        )
        self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        deliveries = ContentDelivery.objects.filter(
            valid_until__lt=timezone.now(),
            enrollment__status=EnrollmentStatus.ACTIVE,
        )

        for delivery in deliveries:
            if not delivery.course_content.quiz:
                continue

            if not delivery.course_content.quiz.is_blocking:
                # If the quiz is non-blocking, we do not want to deactivate the enrollment.
                # Instead, we simply skip to the next delivery.
                logger.info(
                    f"Skipping deactivation for enrollment {delivery.enrollment.id} because \
                     quiz {delivery.course_content.quiz.title} is non-blocking."
                )
                delivery.schedule_next_delivery()
                delivery.valid_until = None  # Clear the valid_until since we've scheduled the next delivery
                delivery.save()
                continue

            enrollment = delivery.enrollment
            enrollment.status = EnrollmentStatus.DEACTIVATED
            enrollment.deactivation_reason = DeactivationReason.INACTIVE
            enrollment.save()
            quiz = delivery.course_content.quiz
            course_title = delivery.course_content.course.title
            logger.info(
                f"Deactivated enrollment {enrollment.id} for learner {mask_email(enrollment.learner.email)} due to \
                missed deadline for quiz {quiz.title} in course {course_title}."
            )

            self.send_deactivation_email(
                enrollment.learner.email,
                quiz,
                course_title,
                delivery.course_content.course.organization.name,
            )
            metric_service.user_enrollment_deactivated(
                course_slug=delivery.course_content.course.slug,
                organization_id=delivery.course_content.course.organization.id,
                reason=DeactivationReason.INACTIVE.value,
            )

        job_execution.status = JobStatus.COMPLETED.value
        job_execution.finished_at = timezone.now()
        job_execution.save()

    def send_deactivation_email(
        self, email: str, quiz: Quiz, course_title: str, organization_name: str
    ) -> None:
        email_service = EmailSenderService()
        subject = _("Your quiz deadline has passed — enrollment deactivated")
        context = {
            "quiz": quiz,
            "course_title": course_title,
            "organization_name": organization_name,
        }
        body = render_to_string(
            "emails/deactivation_deadline_passed.txt",
            context,
        )
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_service.from_email,
            to=[email],
        )
        email_message.attach_alternative(
            render_to_string("emails/deactivation_deadline_passed.html", context),
            "text/html",
        )

        email_service.send(email_message)
