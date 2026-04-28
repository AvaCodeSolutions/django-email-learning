from typing import Protocol
from django_email_learning.models import DeactivationReason


class MetricRecorderProtocol(Protocol):
    def user_enrolled_in_course(self, course_slug: str, organization_id: int) -> None:
        ...

    def quiz_sent(self, course_slug: str, organization_id: int, quiz_id: int) -> None:
        ...

    def quiz_reminder_sent(
        self, course_slug: str, organization_id: int, quiz_id: int
    ) -> None:
        ...

    def lesson_sent(
        self, course_slug: str, organization_id: int, lesson_id: int
    ) -> None:
        ...

    def user_enrollment_activated(self, course_slug: str, organization_id: int) -> None:
        ...

    def user_enrollment_deactivated(
        self, course_slug: str, organization_id: int, reason: DeactivationReason
    ) -> None:
        ...

    def user_completed_course(self, course_slug: str, organization_id: int) -> None:
        ...

    def quiz_submitted(
        self,
        course_slug: str,
        organization_id: int,
        quiz_id: int,
        is_passed: bool,
        is_blocking: bool,
    ) -> None:
        ...

    def method_executed(self, method_name: str, execution_time: int) -> None:
        ...

    def delivery_schedule_blocked(self, content_id: int) -> None:
        ...

    def reminder_schedule_blocked(self, content_id: int) -> None:
        ...

    def imap_command_handling_failed(
        self, imap_connection_id: int, organization_id: int
    ) -> None:
        ...

    def job_execution_started(self, job_name: str) -> None:
        ...

    def job_execution_finished(self, job_name: str, execution_time: int) -> None:
        ...

    def job_execution_failed(self, job_name: str) -> None:
        ...
