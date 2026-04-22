from unittest.mock import Mock, patch

import pytest

from django_email_learning.services.defaults.log_based_metric_recorder import (
    LogBasedMetricRecorder,
)
from django_email_learning.services.metrics_service import MetricsService


class ConfiguredMetricRecorder:
    def user_enrolled_in_course(self, course_slug: str, organization_id: int) -> None:
        pass

    def quiz_sent(self, course_slug: str, organization_id: int, quiz_id: int) -> None:
        pass

    def lesson_sent(
        self, course_slug: str, organization_id: int, lesson_id: int
    ) -> None:
        pass

    def user_enrollment_activated(self, course_slug: str, organization_id: int) -> None:
        pass

    def user_enrollment_deactivated(
        self, course_slug: str, organization_id: int, reason
    ) -> None:
        pass

    def user_completed_course(self, course_slug: str, organization_id: int) -> None:
        pass

    def quiz_submitted(
        self,
        course_slug: str,
        organization_id: int,
        quiz_id: int,
        is_passed: bool,
        is_blocking: bool,
    ) -> None:
        pass

    def method_executed(self, method_name: str, execution_time: int) -> None:
        pass


def test_metrics_service_uses_default_recorder_when_setting_missing(settings):
    settings.DJANGO_EMAIL_LEARNING = {}

    service = MetricsService()

    assert isinstance(service.metric_recorder, LogBasedMetricRecorder)


def test_metrics_service_instantiates_configured_recorder_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "METRIC_RECORDER": "tests.services.test_metrics_service.ConfiguredMetricRecorder"
    }

    service = MetricsService()

    assert isinstance(service.metric_recorder, ConfiguredMetricRecorder)


def test_metrics_service_uses_configured_recorder_object_as_is(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "METRIC_RECORDER": "tests.services.test_metrics_service.ConfiguredMetricRecorder"
    }
    prebuilt_recorder = Mock()

    with patch(
        "django_email_learning.services.metrics_service.import_string",
        return_value=prebuilt_recorder,
    ):
        service = MetricsService()

    assert service.metric_recorder is prebuilt_recorder


@pytest.mark.parametrize(
    "method_name,args",
    [
        ("user_enrolled_in_course", ("course-1", 11)),
        ("quiz_sent", ("course-1", 11, 7)),
        ("lesson_sent", ("course-1", 11, 9)),
        ("user_enrollment_activated", ("course-1", 11)),
        ("user_enrollment_deactivated", ("course-1", 11, "inactive")),
        ("user_completed_course", ("course-1", 11)),
        ("quiz_submitted", ("course-1", 11, 7, True, False)),
        ("method_executed", ("deliver_contents", 123)),
    ],
)
def test_metrics_service_delegates_all_calls(method_name, args):
    service = MetricsService.__new__(MetricsService)
    recorder = Mock()
    service.metric_recorder = recorder

    getattr(service, method_name)(*args)

    getattr(recorder, method_name).assert_called_once_with(*args)


def test_metrics_service_raises_import_error_for_invalid_configured_path(settings):
    settings.DJANGO_EMAIL_LEARNING = {"METRIC_RECORDER": "not.a.real.path.Recorder"}

    with pytest.raises(ImportError):
        MetricsService()
