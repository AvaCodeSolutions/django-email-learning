"""Reminding learners whose enrollment is still unverified a while after they enrolled.

Each unverified enrollment is reminded at most once, `AFTER_HOURS` after enrolling:

* in a course confirmed by email link, with a built-in reminder carrying a fresh
  verification link;
* in a course with an enrollment gate, only when the course turns reminders on, with the
  course's own reminder text.

Enrollments older than `MAX_AGE_DAYS` are left alone, so the first run after an upgrade
doesn't email learners who abandoned their enrollment long ago. Both are read from
``DJANGO_EMAIL_LEARNING["ENROLLMENT_REMINDERS"]`` and can be overridden per run.
"""

import logging
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.models import (
    Enrollment,
    EnrollmentConfirmation,
    EnrollmentStatus,
    JobExecution,
    JobName,
    JobStatus,
)
from django_email_learning.services.enrollment_emails import (
    enrollment_reminder_body,
    has_content,
    send_enrollment_reminder,
    send_verification_reminder,
)
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

DEFAULT_AFTER_HOURS = 24
DEFAULT_MAX_AGE_DAYS = 7


def _reminder_settings() -> dict:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return conf.get("ENROLLMENT_REMINDERS", {})


class SendEnrollmentRemindersJob:
    def __init__(self, after_hours: Optional[int] = None, max_age_days: Optional[int] = None) -> None:
        conf = _reminder_settings()
        self.after_hours = int(after_hours if after_hours is not None else conf.get("AFTER_HOURS", DEFAULT_AFTER_HOURS))
        self.max_age_days = int(
            max_age_days if max_age_days is not None else conf.get("MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS)
        )
        if self.after_hours < 1:
            raise ValueError("AFTER_HOURS must be at least 1.")
        if self.max_age_days * 24 <= self.after_hours:
            raise ValueError("MAX_AGE_DAYS must cover more time than AFTER_HOURS, or no enrollment is ever due.")

    def start(self) -> JobExecution | None:
        job_execution = JobExecution.start_if_not_running(job_name=JobName.SEND_ENROLLMENT_REMINDERS.value)
        if job_execution is None:
            logger.warning("Another instance of SEND_ENROLLMENT_REMINDERS is already running. Exiting this run.")
        return job_execution

    def run(self) -> None:
        job_execution = self.start()
        if job_execution is not None:
            self._run_job(job_execution)

    def due_enrollments(self) -> models.QuerySet[Enrollment]:
        now = timezone.now()
        return (
            Enrollment.objects.filter(
                status=EnrollmentStatus.UNVERIFIED,
                enrollment_reminder_sent_at__isnull=True,
                course__enabled=True,
                enrolled_at__lte=now - timedelta(hours=self.after_hours),
                enrolled_at__gte=now - timedelta(days=self.max_age_days),
            )
            .filter(
                models.Q(course__enrollment_confirmation=EnrollmentConfirmation.LINK)
                | models.Q(
                    course__enrollment_confirmation=EnrollmentConfirmation.GATE,
                    course__enrollment_reminder_enabled=True,
                )
            )
            .select_related("course__organization", "course__imap_connection", "learner")
            .order_by("id")
        )

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.SEND_ENROLLMENT_REMINDERS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        sent = 0
        for enrollment in self.due_enrollments():
            if self.remind(enrollment):
                sent += 1
        logger.info(f"Sent {sent} enrollment reminder(s).")

        job_execution.status = JobStatus.COMPLETED.value
        job_execution.finished_at = timezone.now()
        job_execution.save()

    def remind(self, enrollment: Enrollment) -> bool:
        """Send `enrollment` its reminder, unless another run already has. Returns whether it was sent."""
        course = enrollment.course
        gated = course.is_enrollment_gated
        if gated and not has_content(enrollment_reminder_body(course)):
            return False

        reminder_type = "enrollment" if gated else "verification"
        # Claimed before sending, so two runs racing for the same enrollment send it once.
        claimed = Enrollment.objects.filter(
            id=enrollment.id, status=EnrollmentStatus.UNVERIFIED, enrollment_reminder_sent_at__isnull=True
        ).update(enrollment_reminder_sent_at=timezone.now(), enrollment_reminder_type=reminder_type)
        if not claimed:
            return False

        try:
            if gated:
                send_enrollment_reminder(enrollment)
            else:
                send_verification_reminder(enrollment)
        except Exception:
            # Released again, so the next run retries it rather than recording a reminder never sent.
            Enrollment.objects.filter(id=enrollment.id).update(
                enrollment_reminder_sent_at=None, enrollment_reminder_type=None
            )
            logger.exception(f"Sending the enrollment reminder for enrollment {enrollment.id} failed.")
            return False

        logger.info(
            f"Sent the {reminder_type} reminder for enrollment {enrollment.id}"
            f" to {mask_email(enrollment.learner.email)}."
        )
        return True
