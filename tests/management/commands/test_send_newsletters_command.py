import logging
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from django_email_learning.models import JobName


def test_runs_job_and_prints_success_message() -> None:
    stdout = StringIO()

    with (
        patch("django_email_learning.management.commands.send_newsletters.logging.basicConfig") as mock_basic_config,
        patch("django_email_learning.management.commands.send_newsletters.SendNewslettersJob") as mock_job_cls,
    ):
        call_command("send_newsletters", stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.INFO
    mock_job_cls.return_value.run.assert_called_once_with()
    assert "Send newsletters job completed successfully" in stdout.getvalue()


def test_enables_debug_logging_when_verbose_option_used() -> None:
    stdout = StringIO()

    with (
        patch("django_email_learning.management.commands.send_newsletters.logging.basicConfig") as mock_basic_config,
        patch("django_email_learning.management.commands.send_newsletters.SendNewslettersJob"),
    ):
        call_command("send_newsletters", verbose=True, stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.DEBUG


def test_handles_keyboard_interrupt_without_raising() -> None:
    stdout = StringIO()

    with patch("django_email_learning.management.commands.send_newsletters.SendNewslettersJob") as mock_job_cls:
        mock_job_cls.return_value.run.side_effect = KeyboardInterrupt()

        call_command("send_newsletters", stdout=stdout)

    assert "Send newsletters job interrupted by user" in stdout.getvalue()


def test_records_metric_and_reraises_when_job_fails() -> None:
    stdout = StringIO()

    with (
        patch("django_email_learning.management.commands.send_newsletters.SendNewslettersJob") as mock_job_cls,
        patch(
            "django_email_learning.management.commands.send_newsletters.metric_service.job_execution_failed"
        ) as mock_job_execution_failed,
    ):
        mock_job_cls.return_value.run.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            call_command("send_newsletters", stdout=stdout)

    mock_job_execution_failed.assert_called_once_with(job_name=JobName.SEND_NEWSLETTERS.value)
    assert "Send newsletters job failed: boom" in stdout.getvalue()
