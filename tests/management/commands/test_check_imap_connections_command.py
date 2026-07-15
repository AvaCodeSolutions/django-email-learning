import logging
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


def test_runs_job_and_prints_success_message() -> None:
    stdout = StringIO()

    with (
        patch(
            "django_email_learning.management.commands.check_imap_connections.logging.basicConfig"
        ) as mock_basic_config,
        patch("django_email_learning.management.commands.check_imap_connections.CheckIMAPJob") as mock_job_cls,
    ):
        call_command("check_imap_connections", stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.INFO
    mock_job_cls.return_value.run.assert_called_once_with()
    assert "Check IMAP job completed successfully" in stdout.getvalue()


def test_enables_debug_logging_when_verbose_option_used() -> None:
    stdout = StringIO()

    with (
        patch(
            "django_email_learning.management.commands.check_imap_connections.logging.basicConfig"
        ) as mock_basic_config,
        patch("django_email_learning.management.commands.check_imap_connections.CheckIMAPJob"),
    ):
        call_command("check_imap_connections", verbose=True, stdout=stdout)

    assert mock_basic_config.call_count == 1
    assert mock_basic_config.call_args.kwargs["level"] == logging.DEBUG


def test_handles_keyboard_interrupt_without_raising() -> None:
    stdout = StringIO()

    with patch("django_email_learning.management.commands.check_imap_connections.CheckIMAPJob") as mock_job_cls:
        mock_job_cls.return_value.run.side_effect = KeyboardInterrupt()

        call_command("check_imap_connections", stdout=stdout)

    assert "Check IMAP job interrupted by user" in stdout.getvalue()


def test_reraises_and_logs_error_when_job_fails() -> None:
    stdout = StringIO()

    with patch("django_email_learning.management.commands.check_imap_connections.CheckIMAPJob") as mock_job_cls:
        mock_job_cls.return_value.run.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            call_command("check_imap_connections", stdout=stdout)

    assert "Check IMAP job failed: boom" in stdout.getvalue()
