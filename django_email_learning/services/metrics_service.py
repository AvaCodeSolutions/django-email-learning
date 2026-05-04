from django.conf import settings
from django.utils.module_loading import import_string


class MetricsService:
    def __init__(self) -> None:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            configured_metric_recorder = import_string(
                DJANGO_EMAIL_LEARNING_SETTINGS["METRIC_RECORDER"]
            )
            self.metric_recorder = (
                configured_metric_recorder()
                if isinstance(configured_metric_recorder, type)
                else configured_metric_recorder
            )
        except KeyError:
            from django_email_learning.services.defaults.log_based_metric_recorder import (
                LogBasedMetricRecorder,
            )

            self.metric_recorder = LogBasedMetricRecorder()

    def user_enrolled_in_course(self, course_slug: str, organization_id: int) -> None:
        self.metric_recorder.user_enrolled_in_course(course_slug, organization_id)

    def quiz_sent(self, course_slug: str, organization_id: int, quiz_id: int) -> None:
        self.metric_recorder.quiz_sent(course_slug, organization_id, quiz_id)

    def quiz_reminder_sent(
        self, course_slug: str, organization_id: int, quiz_id: int
    ) -> None:
        self.metric_recorder.quiz_reminder_sent(course_slug, organization_id, quiz_id)

    def lesson_sent(
        self, course_slug: str, organization_id: int, lesson_id: int
    ) -> None:
        self.metric_recorder.lesson_sent(course_slug, organization_id, lesson_id)

    def user_enrollment_activated(self, course_slug: str, organization_id: int) -> None:
        self.metric_recorder.user_enrollment_activated(course_slug, organization_id)

    def user_enrollment_deactivated(
        self, course_slug: str, organization_id: int, reason: str
    ) -> None:
        self.metric_recorder.user_enrollment_deactivated(
            course_slug, organization_id, reason
        )

    def user_completed_course(self, course_slug: str, organization_id: int) -> None:
        self.metric_recorder.user_completed_course(course_slug, organization_id)

    def assignment_submitted(
        self,
        course_slug: str,
        organization_id: int,
        assignment_id: int,
    ) -> None:
        self.metric_recorder.assignment_submitted(
            course_slug, organization_id, assignment_id
        )

    def quiz_submitted(
        self,
        course_slug: str,
        organization_id: int,
        quiz_id: int,
        is_passed: bool,
        is_blocking: bool,
    ) -> None:
        self.metric_recorder.quiz_submitted(
            course_slug, organization_id, quiz_id, is_passed, is_blocking
        )

    def method_executed(self, method_name: str, execution_time: int) -> None:
        self.metric_recorder.method_executed(method_name, execution_time)

    def delivery_schedule_blocked(self, content_id: int) -> None:
        self.metric_recorder.delivery_schedule_blocked(content_id)

    def reminder_schedule_blocked(self, content_id: int) -> None:
        self.metric_recorder.reminder_schedule_blocked(content_id)

    def imap_command_handling_failed(
        self, imap_connection_id: int, organization_id: int
    ) -> None:
        self.metric_recorder.imap_command_handling_failed(
            imap_connection_id, organization_id
        )

    def job_execution_started(self, job_name: str) -> None:
        self.metric_recorder.job_execution_started(job_name)

    def job_execution_finished(self, job_name: str, execution_time: int) -> None:
        self.metric_recorder.job_execution_finished(job_name, execution_time)

    def job_execution_failed(self, job_name: str) -> None:
        self.metric_recorder.job_execution_failed(job_name)
