from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from django_email_learning.models import Newsletter, NewsletterSubscriber, Sendout, SendoutDelivery
from django_email_learning.services.defaults.database_sendout_queue import DatabaseSendoutQueue

RESOLVER_CALLS: list[int] = []


def always_allow_resolver(sendout: Sendout) -> bool:
    RESOLVER_CALLS.append(sendout.id)
    return True


def always_deny_resolver(sendout: Sendout) -> bool:
    RESOLVER_CALLS.append(sendout.id)
    return False


@pytest.fixture(autouse=True)
def _clear_resolver_calls():
    RESOLVER_CALLS.clear()
    yield
    RESOLVER_CALLS.clear()


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


@pytest.fixture()
def sendout(newsletter):
    return Sendout.objects.create(
        newsletter=newsletter,
        subject="Hello",
        body="Body text",
        scheduled_at=timezone.now() - timedelta(minutes=1),
        status=Sendout.Status.SCHEDULED,
    )


@pytest.fixture()
def subscriber(newsletter):
    return NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="sub@example.com", confirmed_at=timezone.now()
    )


def test_fanout_allows_sendout_when_resolver_not_configured(db, sendout, subscriber):
    queue = DatabaseSendoutQueue()

    task = queue.next_task()

    assert task is not None
    assert task.sendout_id == sendout.id
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED
    assert sendout.blocked_reason is None


def test_fanout_excludes_unconfirmed_subscribers(db, newsletter, sendout, subscriber):
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="unconfirmed@example.com")
    queue = DatabaseSendoutQueue()

    task = queue.next_task()

    assert task is not None
    assert list(SendoutDelivery.objects.values_list("subscriber_id", flat=True)) == [subscriber.id]


def test_fanout_receives_the_sendout_instance(db, settings, sendout, subscriber):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {
            "SENDOUT_ALLOWED_RESOLVER": "tests.services.defaults.test_database_sendout_queue.always_allow_resolver",
        },
    }
    queue = DatabaseSendoutQueue()

    queue.next_task()

    assert RESOLVER_CALLS == [sendout.id]


def test_fanout_blocks_sendout_denied_by_resolver(db, settings, sendout, subscriber):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {
            "SENDOUT_ALLOWED_RESOLVER": "tests.services.defaults.test_database_sendout_queue.always_deny_resolver",
        },
    }

    with patch(
        "django_email_learning.services.defaults.database_sendout_queue.metric_service.sendout_blocked_by_resolver"
    ) as mock_metric:
        task = DatabaseSendoutQueue().next_task()

    assert task is None
    assert SendoutDelivery.objects.filter(sendout=sendout).count() == 0
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.BLOCKED
    assert sendout.blocked_reason == Sendout.BlockedReason.DENIED_BY_RESOLVER
    mock_metric.assert_called_once_with(sendout_id=sendout.id, newsletter_id=sendout.newsletter_id)


def test_blocked_sendout_is_not_polled_again(db, sendout, subscriber):
    Sendout.objects.filter(id=sendout.id).update(
        status=Sendout.Status.BLOCKED,
        blocked_reason=Sendout.BlockedReason.DENIED_BY_RESOLVER,
    )

    task = DatabaseSendoutQueue().next_task()

    assert task is None
    assert SendoutDelivery.objects.filter(sendout=sendout).count() == 0


# --- Skipping sendouts with nobody to send to ---


@pytest.mark.parametrize("with_unconfirmed_subscriber", [False, True])
def test_sendout_without_confirmed_subscribers_is_skipped(db, newsletter, sendout, with_unconfirmed_subscriber):
    if with_unconfirmed_subscriber:
        NewsletterSubscriber.objects.create(newsletter=newsletter, email="unconfirmed@example.com")

    with patch(
        "django_email_learning.services.defaults.database_sendout_queue.metric_service.sendout_skipped"
    ) as mock_metric:
        task = DatabaseSendoutQueue().next_task()

    assert task is None
    assert SendoutDelivery.objects.count() == 0
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SKIPPED
    assert sendout.skipped_reason == Sendout.SkippedReason.NO_CONFIRMED_SUBSCRIBERS
    assert sendout.sent_at is None
    mock_metric.assert_called_once_with(
        sendout_id=sendout.id,
        newsletter_id=sendout.newsletter_id,
        reason="no_confirmed_subscribers",
    )


def test_sendout_not_yet_due_is_not_skipped(db, sendout):
    Sendout.objects.filter(id=sendout.id).update(scheduled_at=timezone.now() + timedelta(hours=1))

    assert DatabaseSendoutQueue().next_task() is None

    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED
    assert sendout.skipped_reason is None


def test_sendout_with_existing_deliveries_is_not_skipped(db, newsletter, sendout, subscriber):
    """A sendout partway through sending must finish even if every subscriber
    has since unsubscribed."""
    SendoutDelivery.objects.create(sendout=sendout, subscriber=subscriber)
    NewsletterSubscriber.objects.filter(id=subscriber.id).update(confirmed_at=None)

    task = DatabaseSendoutQueue().next_task()

    assert task is not None
    assert task.sendout_id == sendout.id
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED


def test_skipped_sendouts_do_not_hold_up_others(db, newsletter, subscriber):
    empty_newsletter = Newsletter.objects.create(title="Empty", language="en", organization_id=1)
    due = timezone.now() - timedelta(minutes=1)
    for i in range(60):
        Sendout.objects.create(newsletter=empty_newsletter, subject=f"Empty {i}", body="Body", scheduled_at=due)
    real = Sendout.objects.create(newsletter=newsletter, subject="Real", body="Body", scheduled_at=due)

    queue = DatabaseSendoutQueue()
    tasks = []
    while (task := queue.next_task()) is not None:
        tasks.append(task)

    assert [t.sendout_id for t in tasks] == [real.id]
    assert Sendout.objects.filter(newsletter=empty_newsletter, status=Sendout.Status.SKIPPED).count() == 60


def test_skipped_sendout_is_not_polled_again(db, sendout, subscriber):
    Sendout.objects.filter(id=sendout.id).update(
        status=Sendout.Status.SKIPPED,
        skipped_reason=Sendout.SkippedReason.NO_CONFIRMED_SUBSCRIBERS,
    )

    assert DatabaseSendoutQueue().next_task() is None
    assert SendoutDelivery.objects.filter(sendout=sendout).count() == 0
