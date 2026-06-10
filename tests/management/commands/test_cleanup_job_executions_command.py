from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from django_email_learning.models import JobExecution, JobName, JobStatus



def _create_job_execution(
    *,
    job_name: str,
    status: str,
    finished_at=None,
) -> JobExecution:
    return JobExecution.objects.create(
        job_name=job_name,
        status=status,
        finished_at=finished_at,
    )


def test_rejects_non_positive_days(db) -> None:
    stdout = StringIO()

    call_command("cleanup_job_executions", days=0, stdout=stdout)

    assert "--days must be a positive integer" in stdout.getvalue()


def test_dry_run_reports_candidates_without_deleting(db) -> None:
    cutoff_time = timezone.now() - timedelta(days=3)
    old_execution = _create_job_execution(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.COMPLETED.value,
        finished_at=cutoff_time,
    )
    _create_job_execution(
        job_name=JobName.DELIVER_CONTENTS.value,
        status=JobStatus.COMPLETED.value,
        finished_at=timezone.now(),
    )

    stdout = StringIO()
    call_command("cleanup_job_executions", days=2, dry_run=True, stdout=stdout)

    assert "Dry run: 1 completed/staled job executions older than 2 days" in stdout.getvalue()
    assert JobExecution.objects.filter(pk=old_execution.pk).exists()


def test_deletes_only_old_completed_rows(db) -> None:
    cutoff_time = timezone.now() - timedelta(days=3)

    old_completed = _create_job_execution(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.COMPLETED.value,
        finished_at=cutoff_time,
    )
    old_running = _create_job_execution(
        job_name=JobName.DELIVER_CONTENTS.value,
        status=JobStatus.RUNNING.value,
        finished_at=cutoff_time,
    )
    no_finished_at = _create_job_execution(
        job_name=JobName.SEND_REMINDERS.value,
        status=JobStatus.COMPLETED.value,
        finished_at=None,
    )
    recent_completed = _create_job_execution(
        job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
        status=JobStatus.COMPLETED.value,
        finished_at=timezone.now(),
    )

    stdout = StringIO()
    call_command("cleanup_job_executions", days=2, stdout=stdout)

    assert "Deleted 1 completed/staled job executions older than 2 days" in stdout.getvalue()
    assert not JobExecution.objects.filter(pk=old_completed.pk).exists()
    assert JobExecution.objects.filter(pk=old_running.pk).exists()
    assert JobExecution.objects.filter(pk=no_finished_at.pk).exists()
    assert JobExecution.objects.filter(pk=recent_completed.pk).exists()


def test_deletes_old_stale_rows(db) -> None:
    cutoff_time = timezone.now() - timedelta(days=3)

    old_stale = _create_job_execution(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.STALE.value,
        finished_at=cutoff_time,
    )
    recent_stale = _create_job_execution(
        job_name=JobName.DELIVER_CONTENTS.value,
        status=JobStatus.STALE.value,
        finished_at=timezone.now(),
    )

    stdout = StringIO()
    call_command("cleanup_job_executions", days=2, stdout=stdout)

    assert not JobExecution.objects.filter(pk=old_stale.pk).exists()
    assert JobExecution.objects.filter(pk=recent_stale.pk).exists()
