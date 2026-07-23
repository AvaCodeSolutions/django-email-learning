import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import Newsletter, NewsletterSubscriber


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


@pytest.fixture()
def subscriber(newsletter):
    return NewsletterSubscriber.objects.create(
        newsletter=newsletter,
        email="reader@example.com",
    )


def confirm_url(token):
    return reverse(
        "django_email_learning:public:newsletter_confirm_subscription",
        kwargs={"token": token},
    )


def test_valid_token_confirms_subscription(db, anonymous_client, subscriber):
    assert not subscriber.is_confirmed

    response = anonymous_client.get(confirm_url(subscriber.confirm_token))

    assert response.status_code == 200
    subscriber.refresh_from_db()
    assert subscriber.is_confirmed


def test_valid_token_shows_newsletter_title(db, anonymous_client, subscriber):
    response = anonymous_client.get(confirm_url(subscriber.confirm_token))

    assert "Weekly Digest" in response.content.decode()


def test_invalid_token_returns_410(db, anonymous_client):
    response = anonymous_client.get(confirm_url(uuid.uuid4()))

    assert response.status_code == 410


def test_confirming_twice_is_idempotent(db, anonymous_client, subscriber):
    token = subscriber.confirm_token
    anonymous_client.get(confirm_url(token))
    subscriber.refresh_from_db()
    first_confirmed_at = subscriber.confirmed_at

    response = anonymous_client.get(confirm_url(token))

    assert response.status_code == 200
    subscriber.refresh_from_db()
    assert subscriber.confirmed_at == first_confirmed_at


def test_confirm_does_not_affect_other_subscribers(db, anonymous_client, newsletter, subscriber):
    other = NewsletterSubscriber.objects.create(
        newsletter=newsletter,
        email="other@example.com",
    )
    anonymous_client.get(confirm_url(subscriber.confirm_token))

    other.refresh_from_db()
    assert not other.is_confirmed


def test_already_confirmed_subscriber_shows_confirmed_page(db, anonymous_client, subscriber):
    subscriber.confirmed_at = timezone.now()
    subscriber.save(update_fields=["confirmed_at"])

    response = anonymous_client.get(confirm_url(subscriber.confirm_token))

    assert response.status_code == 200
    assert "Weekly Digest" in response.content.decode()
