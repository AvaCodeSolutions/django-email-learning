from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from django_email_learning.jobs.send_newsletters_job import (
    SendNewslettersJob,
    _get_newsletter_from_email,
)
from django_email_learning.models import (
    JobExecution,
    JobName,
    JobStatus,
    Newsletter,
    NewsletterSubscriber,
    Sendout,
    SendoutDelivery,
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
def subscriber(newsletter):
    return NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="sub@example.com"
    )


@pytest.fixture()
def delivery(sendout, subscriber):
    return SendoutDelivery.objects.create(
        sendout=sendout,
        subscriber=subscriber,
        status=SendoutDelivery.Status.PROCESSING,
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


# ── run() orchestration ──────────────────────────────────────────────────────


def test_run_exits_when_already_running(db, job):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.JobExecution.start_if_not_running",
        return_value=None,
    ):
        job.run()

    job.sendout_queue.next_task.assert_not_called()


def test_run_no_tasks_completes_job_execution(db, job, sendout_queue_mock):
    sendout_queue_mock.next_task.return_value = None

    job.run()

    execution = JobExecution.objects.filter(job_name=JobName.SEND_NEWSLETTERS).first()
    assert execution is not None
    assert execution.status == JobStatus.COMPLETED


# ── process_delivery: success path ──────────────────────────────────────────


def test_process_delivery_success_marks_delivery_sent(db, delivery):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send"
    ):
        SendNewslettersJob().process_delivery(delivery)

    delivery.refresh_from_db()
    assert delivery.status == SendoutDelivery.Status.SENT
    assert delivery.sent_at is not None


def test_process_delivery_success_marks_sendout_sent_when_last(db, delivery, sendout):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send"
    ):
        SendNewslettersJob().process_delivery(delivery)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SENT
    assert sendout.sent_at is not None


def test_process_delivery_sendout_stays_scheduled_while_others_pending(
    db, sendout, newsletter
):
    sub1 = NewsletterSubscriber.objects.create(newsletter=newsletter, email="a@x.com")
    sub2 = NewsletterSubscriber.objects.create(newsletter=newsletter, email="b@x.com")
    d1 = SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub1, status=SendoutDelivery.Status.PROCESSING
    )
    SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub2, status=SendoutDelivery.Status.PENDING
    )

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send"
    ):
        SendNewslettersJob().process_delivery(d1)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED


# ── process_delivery: retry path ─────────────────────────────────────────────


def test_process_delivery_failure_increments_retry_and_sets_pending(db, delivery):
    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=RuntimeError("smtp error"),
    ):
        SendNewslettersJob().process_delivery(delivery)

    delivery.refresh_from_db()
    assert delivery.status == SendoutDelivery.Status.PENDING
    assert delivery.retry_count == 1


def test_process_delivery_marks_failed_after_max_retries_when_others_succeeded(
    db, sendout, newsletter, settings
):
    """A delivery that hits max retries stays FAILED when at least one sibling succeeded."""
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"MAX_RETRIES": 1},
    }
    sub_ok = NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="ok@x.com"
    )
    sub_bad = NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="bad@x.com"
    )
    SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub_ok, status=SendoutDelivery.Status.SENT
    )
    d_fail = SendoutDelivery.objects.create(
        sendout=sendout,
        subscriber=sub_bad,
        status=SendoutDelivery.Status.PROCESSING,
        retry_count=0,
    )

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=RuntimeError("smtp error"),
    ):
        SendNewslettersJob().process_delivery(d_fail)

    d_fail.refresh_from_db()
    assert d_fail.status == SendoutDelivery.Status.FAILED
    assert d_fail.retry_count == 1


def test_process_delivery_only_retries_failed_subscriber_not_others(
    db, sendout, newsletter, settings
):
    """A failure on one delivery must not affect the others."""
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"MAX_RETRIES": 3},
    }
    sub1 = NewsletterSubscriber.objects.create(newsletter=newsletter, email="ok@x.com")
    sub2 = NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="fail@x.com"
    )
    d_ok = SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub1, status=SendoutDelivery.Status.PROCESSING
    )
    d_fail = SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub2, status=SendoutDelivery.Status.PROCESSING
    )

    call_count = 0

    def fail_second(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("smtp error")

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=fail_second,
    ):
        job = SendNewslettersJob()
        job.process_delivery(d_ok)
        job.process_delivery(d_fail)

    d_ok.refresh_from_db()
    d_fail.refresh_from_db()
    assert d_ok.status == SendoutDelivery.Status.SENT
    assert d_fail.status == SendoutDelivery.Status.PENDING
    assert d_fail.retry_count == 1


# ── sendout best-effort completion ───────────────────────────────────────────


def test_sendout_marked_sent_when_all_deliveries_done_best_effort(
    db, sendout, newsletter, settings
):
    """Sendout becomes SENT even if one delivery permanently failed."""
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"MAX_RETRIES": 1},
    }
    sub1 = NewsletterSubscriber.objects.create(newsletter=newsletter, email="ok@x.com")
    sub2 = NewsletterSubscriber.objects.create(newsletter=newsletter, email="bad@x.com")
    SendoutDelivery.objects.create(
        sendout=sendout, subscriber=sub1, status=SendoutDelivery.Status.SENT
    )
    d_fail = SendoutDelivery.objects.create(
        sendout=sendout,
        subscriber=sub2,
        status=SendoutDelivery.Status.PROCESSING,
        retry_count=0,
    )

    with patch(
        "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
        side_effect=RuntimeError("smtp error"),
    ):
        SendNewslettersJob().process_delivery(d_fail)

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SENT


def test_sendout_stays_scheduled_and_resets_when_all_deliveries_fail(
    db, sendout, newsletter, settings
):
    """If every delivery permanently fails the sendout stays SCHEDULED and
    deliveries are reset to PENDING so the next run retries them all."""
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"MAX_RETRIES": 1},
    }
    sub = NewsletterSubscriber.objects.create(newsletter=newsletter, email="bad@x.com")
    delivery = SendoutDelivery.objects.create(
        sendout=sendout,
        subscriber=sub,
        status=SendoutDelivery.Status.PROCESSING,
        retry_count=0,
    )

    with (
        patch(
            "django_email_learning.jobs.send_newsletters_job.email_sender_service.send",
            side_effect=RuntimeError("smtp error"),
        ),
        patch(
            "django_email_learning.jobs.send_newsletters_job.metric_service.sendout_all_deliveries_failed"
        ) as mock_metric,
    ):
        SendNewslettersJob().process_delivery(delivery)

    sendout.refresh_from_db()
    delivery.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED
    assert delivery.status == SendoutDelivery.Status.PENDING
    assert delivery.retry_count == 0
    assert sendout.scheduled_at > timezone.now()
    assert sendout.scheduled_at <= timezone.now() + timedelta(minutes=11)
    mock_metric.assert_called_once_with(
        sendout_id=sendout.id, newsletter_id=sendout.newsletter_id
    )


# ── from_email resolution ────────────────────────────────────────────────────


def test_from_email_uses_newsletters_specific_setting(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "FROM_EMAIL": "global@example.com",
        "NEWSLETTERS": {"FROM_EMAIL": "newsletter@example.com"},
    }
    assert _get_newsletter_from_email() == "newsletter@example.com"


def test_from_email_falls_back_to_global_from_email(settings):
    settings.DJANGO_EMAIL_LEARNING = {"FROM_EMAIL": "global@example.com"}
    assert _get_newsletter_from_email() == "global@example.com"


def test_from_email_falls_back_to_default_when_nothing_configured(settings):
    settings.DJANGO_EMAIL_LEARNING = {}
    assert _get_newsletter_from_email() == "webmaster@localhost"
