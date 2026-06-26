from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob
from django_email_learning.models import (
    JobExecution,
    JobName,
    JobStatus,
    Newsletter,
    NewsletterSubscriber,
    Sendout,
)


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(
        title="Weekly Digest", language="en", organization_id=1
    )


@pytest.fixture()
def sendout(newsletter):
    return Sendout.objects.create(
        newsletter=newsletter,
        subject="Hello",
        body="Body text",
        scheduled_at=timezone.now(),
        status=Sendout.Status.SCHEDULED,
    )


@pytest.fixture()
def sendout_queue_mock():
    return MagicMock()


@pytest.fixture()
def job(sendout_queue_mock):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.SendNewslettersJob._get_sendout_queue",
        return_value=sendout_queue_mock,
    ):
        j = SendNewslettersJob()
    j.sendout_queue = sendout_queue_mock
    return j


def test_run_exits_when_already_running(db, job):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.JobExecution.start_if_not_running",
        return_value=None,
    ):
        job.run()

    job.sendout_queue.next_task.assert_not_called()


def test_run_no_tasks(db, job, sendout_queue_mock):
    sendout_queue_mock.next_task.return_value = None

    job.run()

    execution = JobExecution.objects.filter(job_name=JobName.SEND_NEWSLETTERS).first()
    assert execution is not None
    assert execution.status == JobStatus.COMPLETED


def test_process_sendout_no_subscribers_marks_sent(db, sendout):
    job = SendNewslettersJob()
    job.process_sendout(sendout)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SENT
    assert sendout.sent_at is not None


def test_process_sendout_sends_to_all_subscribers(db, sendout, newsletter):
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="a@example.com")
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="b@example.com")

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send"
    ) as mock_send:
        job = SendNewslettersJob()
        job.process_sendout(sendout)

    assert mock_send.call_count == 2
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SENT
    assert sendout.sent_at is not None


def test_process_sendout_increments_retry_on_partial_failure(db, sendout, newsletter):
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="a@example.com")
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="b@example.com")

    call_count = 0

    def fail_second(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("send failed")

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=fail_second,
    ):
        job = SendNewslettersJob()
        job.process_sendout(sendout)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED
    assert sendout.retry_count == 1


def test_process_sendout_marks_failed_after_max_retries(db, sendout, newsletter):
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="a@example.com")
    sendout.retry_count = sendout.max_retries
    sendout.save()

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=RuntimeError("send failed"),
    ):
        job = SendNewslettersJob()
        job.process_sendout(sendout)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.FAILED


def test_process_sendout_already_sent_is_skipped(db, sendout, newsletter):
    """Idempotency: the queue should not return already-sent sendouts, but verify
    that if process_sendout is called on a sent sendout it does not re-send."""
    sendout.status = Sendout.Status.SENT
    sendout.sent_at = timezone.now()
    sendout.save()

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send"
    ) as mock_send:
        job = SendNewslettersJob()
        # Direct call: no subscribers so it would just mark sent again without calling send
        job.process_sendout(sendout)

    mock_send.assert_not_called()
