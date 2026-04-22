from django_email_learning.ports.metric_recorder_protocol import MetricRecorderProtocol
from django_email_learning.models import DeactivationReason
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
