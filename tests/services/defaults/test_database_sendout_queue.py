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
    return NewsletterSubscriber.objects.create(newsletter=newsletter, email="sub@example.com")


def test_fanout_allows_sendout_when_resolver_not_configured(db, sendout, subscriber):
    queue = DatabaseSendoutQueue()

    task = queue.next_task()

    assert task is not None
    assert task.sendout_id == sendout.id
    sendout.refresh_from_db()
    assert sendout.status == Sendout.Status.SCHEDULED
    assert sendout.blocked_reason is None


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
