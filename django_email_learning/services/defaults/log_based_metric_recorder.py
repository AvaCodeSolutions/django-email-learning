from django_email_learning.ports.metric_recorder_protocol import MetricRecorderProtocol
from django_email_learning.models import DeactivationReason
import logging

logger = logging.getLogger(__name__)


class LogBasedMetricRecorder(MetricRecorderProtocol):
    def user_enrolled_in_course(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User enrolled",
            extra={"course_slug": course_slug, "organization_id": organization_id},
        )

    def quiz_sent(self, course_slug: str, organization_id: int, quiz_id: int) -> None:
        logger.info(
            "Quiz sent",
            extra={
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
                "course_slug": course_slug,
                "organization_id": organization_id,
                "lesson_id": lesson_id,
            },
        )

    def user_enrollment_activated(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User enrollment activated",
            extra={"course_slug": course_slug, "organization_id": organization_id},
        )

    def user_enrollment_deactivated(
        self, course_slug: str, organization_id: int, reason: DeactivationReason
    ) -> None:
        logger.info(
            "User enrollment deactivated",
            extra={
                "course_slug": course_slug,
                "organization_id": organization_id,
                "reason": reason,
            },
        )

    def user_completed_course(self, course_slug: str, organization_id: int) -> None:
        logger.info(
            "User completed course",
            extra={"course_slug": course_slug, "organization_id": organization_id},
        )

    def quiz_submitted(
        self, course_slug: str, organization_id: int, quiz_id: int, is_passed: bool
    ) -> None:
        logger.info(
            "Quiz submitted",
            extra={
                "course_slug": course_slug,
                "organization_id": organization_id,
                "quiz_id": quiz_id,
                "is_passed": is_passed,
            },
        )

    def method_executed(self, method_name: str, execution_time: int) -> None:
        logger.info(
            "Method executed",
            extra={"method_name": method_name, "execution_time": execution_time},
        )
