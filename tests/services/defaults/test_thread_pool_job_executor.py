import time
from unittest import mock

import pytest

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import JobExecution, JobName, JobStatus
from django_email_learning.services.defaults.thread_pool_job_executor import ThreadPoolJobExecutor

# The background thread opens its own DB connection, so these need a real
# committed transaction (not pytest-django's default per-test rollback) or
# the two connections deadlock against each other on SQLite.
pytestmark = pytest.mark.django_db(transaction=True)


def _wait_until_finished(job_execution: JobExecution, timeout: float = 5.0) -> JobExecution:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job_execution.refresh_from_db()
        if job_execution.status != JobStatus.RUNNING.value:
            return job_execution
        time.sleep(0.05)
    raise AssertionError(f"job execution {job_execution.id} did not finish within {timeout}s")


def test_submit_runs_the_real_job_and_marks_it_completed() -> None:
    job_execution = JobExecution.objects.create(job_name=JobName.CHECK_IMAP.value, status=JobStatus.RUNNING.value)

    executor = ThreadPoolJobExecutor()
    executor.submit(job_name=JobName.CHECK_IMAP.value, job_execution_id=job_execution.id)

    job_execution = _wait_until_finished(job_execution)

    assert job_execution.status == JobStatus.COMPLETED.value
    assert job_execution.error is None
    assert job_execution.finished_at is not None


def test_submit_marks_job_failed_when_the_job_raises() -> None:
    job_execution = JobExecution.objects.create(job_name=JobName.DELIVER_CONTENTS.value, status=JobStatus.RUNNING.value)

    raising_queue = mock.Mock()
    raising_queue.next_task.side_effect = RuntimeError("boom")

    executor = ThreadPoolJobExecutor()
    with mock.patch.object(DeliverContentsJob, "get_delivery_queue", return_value=raising_queue):
        executor.submit(job_name=JobName.DELIVER_CONTENTS.value, job_execution_id=job_execution.id)
        job_execution = _wait_until_finished(job_execution)

    assert job_execution.status == JobStatus.FAILED.value
    assert job_execution.error == "boom"
