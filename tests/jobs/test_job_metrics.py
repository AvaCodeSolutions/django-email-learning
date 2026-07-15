from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.models import JobExecution, JobName, JobStatus


class DummyMetrics:
    def __init__(self) -> None:
        self.job_execution_started = MagicMock()
        self.job_execution_finished = MagicMock()
        self.job_execution_failed = MagicMock()


def test_track_job_execution_emits_started_and_finished_on_success(db) -> None:
    metrics = DummyMetrics()
    job_execution = JobExecution.objects.create(job_name=JobName.CHECK_IMAP.value, status=JobStatus.RUNNING.value)
    start_time = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=4)

    @track_job_execution(metric_service=metrics, job_name="test_job")
    def decorated_function(self: object, job_execution: JobExecution) -> str:
        return "ok"

    with patch(
        "django_email_learning.jobs.job_metrics.timezone.now",
        side_effect=[start_time, end_time],
    ):
        result = decorated_function(object(), job_execution)

    assert result == "ok"
    metrics.job_execution_started.assert_called_once_with(job_name="test_job")
    metrics.job_execution_finished.assert_called_once_with(job_name="test_job", execution_time=4)
    metrics.job_execution_failed.assert_not_called()


def test_track_job_execution_marks_failed_and_reraises_on_exception(db) -> None:
    metrics = DummyMetrics()
    job_execution = JobExecution.objects.create(job_name=JobName.CHECK_IMAP.value, status=JobStatus.RUNNING.value)
    start_time = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(seconds=5)

    @track_job_execution(metric_service=metrics, job_name="test_job")
    def decorated_function(self: object, job_execution: JobExecution) -> None:
        raise RuntimeError("boom")

    with patch(
        "django_email_learning.jobs.job_metrics.timezone.now",
        side_effect=[start_time, end_time, end_time],
    ):
        with pytest.raises(RuntimeError, match="boom"):
            decorated_function(object(), job_execution)

    metrics.job_execution_started.assert_called_once_with(job_name="test_job")
    metrics.job_execution_failed.assert_called_once_with(job_name="test_job")
    metrics.job_execution_finished.assert_called_once_with(job_name="test_job", execution_time=5)

    job_execution.refresh_from_db()
    assert job_execution.status == JobStatus.FAILED.value
    assert job_execution.error == "boom"
    assert job_execution.finished_at is not None
