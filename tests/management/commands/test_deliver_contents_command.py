import logging
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import JobName


def test_runs_job_and_prints_success_message() -> None:
    stdout = StringIO()

    with (
        patch("django_email_learning.management.commands.deliver_contents.logging.basicConfig") as mock_basic_config,
        patch("django_email_learning.management.commands.deliver_contents.DeliverContentsJob") as mock_job_cls,
    ):
        call_command("deliver_contents", stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.INFO
    mock_job_cls.return_value.run.assert_called_once_with()
    assert "Content delivery job completed successfully" in stdout.getvalue()


def test_enables_debug_logging_when_verbose_option_used() -> None:
    stdout = StringIO()

    with (
        patch("django_email_learning.management.commands.deliver_contents.logging.basicConfig") as mock_basic_config,
        patch("django_email_learning.management.commands.deliver_contents.DeliverContentsJob"),
    ):
        call_command("deliver_contents", verbose=True, stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.DEBUG


def test_handles_keyboard_interrupt_without_raising() -> None:
    stdout = StringIO()

    with patch("django_email_learning.management.commands.deliver_contents.DeliverContentsJob") as mock_job_cls:
        mock_job_cls.return_value.run.side_effect = KeyboardInterrupt()

        call_command("deliver_contents", stdout=stdout)

    assert "Content delivery job interrupted by user" in stdout.getvalue()


def test_reraises_and_logs_error_when_job_fails() -> None:
    stdout = StringIO()

    with patch("django_email_learning.management.commands.deliver_contents.DeliverContentsJob") as mock_job_cls:
        mock_job_cls.return_value.run.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            call_command("deliver_contents", stdout=stdout)

    assert "Content delivery job failed: boom" in stdout.getvalue()


def test_job_execution_failed_metric_recorded_exactly_once_when_job_actually_fails(db) -> None:
    """Regression test: the command used to also call job_execution_failed
    itself, double-counting the metric that track_job_execution now already
    emits from inside the real job's _run_job on failure."""
    stdout = StringIO()
    raising_queue = Mock()
    raising_queue.next_task.side_effect = RuntimeError("boom")

    with (
        patch.object(DeliverContentsJob, "get_delivery_queue", return_value=raising_queue),
        patch("django_email_learning.services.metrics_service.metric_service.job_execution_failed") as mock_failed,
    ):
        with pytest.raises(RuntimeError):
            call_command("deliver_contents", stdout=stdout)

    mock_failed.assert_called_once_with(job_name=JobName.DELIVER_CONTENTS.value)
