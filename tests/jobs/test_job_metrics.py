from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from django_email_learning.jobs.job_metrics import track_job_execution


class DummyMetrics:
    def __init__(self) -> None:
        self.job_execution_started = MagicMock()
        self.job_execution_finished = MagicMock()


def test_track_job_execution_emits_started_and_finished_on_success():
    metrics = DummyMetrics()
    start_time = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=4)

    @track_job_execution(metric_service=metrics, job_name="test_job")
    def decorated_function() -> str:
        return "ok"

    with patch(
        "django_email_learning.jobs.job_metrics.timezone.now",
        side_effect=[start_time, end_time],
    ):
        result = decorated_function()

    assert result == "ok"
    metrics.job_execution_started.assert_called_once_with(job_name="test_job")
    metrics.job_execution_finished.assert_called_once_with(
        job_name="test_job",
        execution_time=4,
    )


def test_track_job_execution_emits_finished_when_wrapped_function_raises():
    metrics = DummyMetrics()
    start_time = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=5)

    @track_job_execution(metric_service=metrics, job_name="test_job")
    def decorated_function() -> None:
        raise RuntimeError("boom")

    with patch(
        "django_email_learning.jobs.job_metrics.timezone.now",
        side_effect=[start_time, end_time],
    ):
        with pytest.raises(RuntimeError, match="boom"):
            decorated_function()

    metrics.job_execution_started.assert_called_once_with(job_name="test_job")
    metrics.job_execution_finished.assert_called_once_with(
        job_name="test_job",
        execution_time=5,
    )
