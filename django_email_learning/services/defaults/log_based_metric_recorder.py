from django_email_learning.ports.metric_recorder_protocol import MetricRecorderProtocol
from django_email_learning.models.enums.deactivation_reason import DeactivationReason
import logging

logger = logging.getLogger(__name__)


class LogBasedMetricRecorder(MetricRecorderProtocol):
    def user_enrolled_in_course(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User enrolled",
            extra={
                "metric": "user_enrolled",
                "course_slug": course_slug,
                "organization_id": organization_id,
            },
        )

    def quiz_sent(self, course_slug: str, organization_id: int, quiz_id: int) -> None:
        logger.info(
            "Quiz sent",
            extra={
                "metric": "quiz_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "quiz_id": quiz_id,
            },
        )

    def assignment_sent(
        self, course_slug: str, organization_id: int, assignment_id: int
    ) -> None:
        logger.info(
            "Assignment sent",
            extra={
                "metric": "assignment_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "assignment_id": assignment_id,
            },
        )

    def quiz_reminder_sent(
        self, course_slug: str, organization_id: int, quiz_id: int
    ) -> None:
        logger.info(
            "Quiz reminder sent",
            extra={
                "metric": "quiz_reminder_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "quiz_id": quiz_id,
            },
        )

    def assignment_reminder_sent(
        self, course_slug: str, organization_id: int, assignment_id: int
    ) -> None:
        logger.info(
            "Assignment reminder sent",
            extra={
                "metric": "assignment_reminder_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "assignment_id": assignment_id,
            },
        )

    def lesson_sent(
        self, course_slug: str, organization_id: int, lesson_id: int
    ) -> None:
        logger.info(
            "Lesson sent",
            extra={
                "metric": "lesson_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "lesson_id": lesson_id,
            },
        )

    def user_enrollment_activated(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User enrollment activated",
            extra={
                "metric": "user_enrollment_activated",
                "course_slug": course_slug,
                "organization_id": organization_id,
            },
        )

    def user_enrollment_deactivated(
        self, course_slug: str, organization_id: int, reason: DeactivationReason
    ) -> None:
        logger.info(
            "User enrollment deactivated",
            extra={
                "metric": "user_enrollment_deactivated",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "reason": reason,
            },
        )

    def user_completed_course(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User completed course",
            extra={
                "metric": "user_completed_course",
                "course_slug": course_slug,
                "organization_id": organization_id,
            },
        )

    def assignment_submitted(
        self, course_slug: str, organization_id: int, assignment_id: int
    ) -> None:
        logger.info(
            "Assignment Submitted",
            extra={
                "metric": "assignment_submitted",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "assignment_id": assignment_id,
            },
        )

    def assignment_review_sent(
        self,
        course_slug: str,
        organization_id: int,
        assignment_id: int,
    ) -> None:
        logger.info(
            "Assignment review sent",
            extra={
                "metric": "assignment_review_sent",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "assignment_id": assignment_id,
            },
        )

    def quiz_submitted(
        self,
        course_slug: str,
        organization_id: int,
        quiz_id: int,
        is_passed: bool,
        is_blocking: bool,
    ) -> None:
        logger.info(
            "Quiz submitted",
            extra={
                "metric": "quiz_submitted",
                "course_slug": course_slug,
                "organization_id": organization_id,
                "quiz_id": quiz_id,
                "is_passed": is_passed,
                "is_blocking": is_blocking,
            },
        )

    def method_executed(self, method_name: str, execution_time: int) -> None:
        logger.info(
            "Method executed",
            extra={
                "metric": "method_executed",
                "method_name": method_name,
                "execution_time": execution_time,
            },
        )

    def delivery_schedule_blocked(self, content_id: int) -> None:
        logger.info(
            "Delivery schedule blocked",
            extra={
                "metric": "delivery_schedule_blocked",
                "content_id": content_id,
            },
        )

    def reminder_schedule_blocked(self, content_id: int) -> None:
        logger.info(
            "Reminder schedule blocked",
            extra={
                "metric": "reminder_schedule_blocked",
                "content_id": content_id,
            },
        )

    def imap_command_handling_failed(
        self, imap_connection_id: int, organization_id: int
    ) -> None:
        logger.warning(
            "IMAP command handling failed",
            extra={
                "metric": "imap_command_handling_failed",
                "imap_connection_id": imap_connection_id,
                "organization_id": organization_id,
            },
        )

    def job_execution_started(self, job_name: str) -> None:
        logger.info(
            "Job execution started",
            extra={
                "metric": "job_execution_started",
                "job_name": job_name,
            },
        )

    def job_execution_finished(self, job_name: str, execution_time: int) -> None:
        logger.info(
            "Job execution finished",
            extra={
                "metric": "job_execution_finished",
                "job_name": job_name,
                "execution_time": execution_time,
            },
        )

    def job_execution_failed(self, job_name: str) -> None:
        logger.error(
            "Job execution failed",
            extra={
                "metric": "job_execution_failed",
                "job_name": job_name,
            },
        )
