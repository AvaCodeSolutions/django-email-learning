from datetime import timedelta

from django.utils import timezone

from django_email_learning.models import JobExecution, JobName, JobStatus


def test_start_if_not_running_creates_execution(db) -> None:
    execution = JobExecution.start_if_not_running(JobName.CHECK_IMAP.value)

    assert execution is not None
    assert execution.status == JobStatus.RUNNING.value
    assert execution.job_name == JobName.CHECK_IMAP.value


def test_start_if_not_running_returns_none_when_already_running(db) -> None:
    JobExecution.start_if_not_running(JobName.CHECK_IMAP.value)

    second = JobExecution.start_if_not_running(JobName.CHECK_IMAP.value)

    assert second is None


def test_start_if_not_running_resets_stale_running_record(db) -> None:
    stale = JobExecution.objects.create(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.RUNNING.value,
    )
    JobExecution.objects.filter(pk=stale.pk).update(started_at=timezone.now() - timedelta(hours=3))

    execution = JobExecution.start_if_not_running(JobName.CHECK_IMAP.value, stale_after_hours=2)

    assert execution is not None
    assert execution.status == JobStatus.RUNNING.value

    stale.refresh_from_db()
    assert stale.status == JobStatus.STALE.value
    assert stale.finished_at is not None


def test_start_if_not_running_does_not_reset_recent_running_record(db) -> None:
    JobExecution.objects.create(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.RUNNING.value,
    )

    execution = JobExecution.start_if_not_running(JobName.CHECK_IMAP.value, stale_after_hours=2)

    assert execution is None
    assert JobExecution.objects.filter(job_name=JobName.CHECK_IMAP.value, status=JobStatus.RUNNING.value).count() == 1


def test_start_if_not_running_only_resets_stale_for_matching_job(db) -> None:
    stale_imap = JobExecution.objects.create(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.RUNNING.value,
    )
    stale_deliver = JobExecution.objects.create(
        job_name=JobName.DELIVER_CONTENTS.value,
        status=JobStatus.RUNNING.value,
    )
    stale_cutoff = timezone.now() - timedelta(hours=3)
    JobExecution.objects.filter(pk__in=[stale_imap.pk, stale_deliver.pk]).update(started_at=stale_cutoff)

    JobExecution.start_if_not_running(JobName.CHECK_IMAP.value, stale_after_hours=2)

    stale_imap.refresh_from_db()
    stale_deliver.refresh_from_db()
    assert stale_imap.status == JobStatus.STALE.value
    assert stale_deliver.status == JobStatus.RUNNING.value
