from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

JOB = "django_email_learning.management.commands.send_enrollment_reminders.SendEnrollmentRemindersJob"


def test_runs_the_job_with_the_configured_window() -> None:
    stdout = StringIO()

    with patch(JOB) as mock_job_cls:
        call_command("send_enrollment_reminders", stdout=stdout)

    mock_job_cls.assert_called_once_with(after_hours=None, max_age_days=None)
    mock_job_cls.return_value.run.assert_called_once_with()
    assert "Send enrollment reminders job completed successfully" in stdout.getvalue()


def test_the_window_can_be_overridden() -> None:
    with patch(JOB) as mock_job_cls:
        call_command("send_enrollment_reminders", "--hours", "12", "--max-age-days", "3", stdout=StringIO())

    mock_job_cls.assert_called_once_with(after_hours=12, max_age_days=3)
