import uuid

import pytest
from django.urls import reverse

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


def unsubscribe_url(token):
    return reverse(
        "django_email_learning:public:newsletter_unsubscribe",
        kwargs={"token": token},
    )


def test_valid_token_unsubscribes_and_returns_200(db, anonymous_client, subscriber):
    token = subscriber.unsubscribe_token
    response = anonymous_client.get(unsubscribe_url(token))

    assert response.status_code == 200
    assert not NewsletterSubscriber.objects.filter(unsubscribe_token=token).exists()


def test_valid_token_shows_newsletter_title(db, anonymous_client, subscriber):
    response = anonymous_client.get(unsubscribe_url(subscriber.unsubscribe_token))

    assert "Weekly Digest" in response.content.decode()


def test_invalid_token_returns_410(db, anonymous_client):
    response = anonymous_client.get(unsubscribe_url(uuid.uuid4()))

    assert response.status_code == 410


def test_already_used_token_returns_410(db, anonymous_client, subscriber):
    token = subscriber.unsubscribe_token
    anonymous_client.get(unsubscribe_url(token))

    # Second request with same token — subscriber is already gone
    response = anonymous_client.get(unsubscribe_url(token))
    assert response.status_code == 410


def test_unsubscribe_does_not_affect_other_subscribers(db, anonymous_client, newsletter, subscriber):
    other = NewsletterSubscriber.objects.create(
        newsletter=newsletter,
        email="other@example.com",
    )
    anonymous_client.get(unsubscribe_url(subscriber.unsubscribe_token))

    assert NewsletterSubscriber.objects.filter(pk=other.pk).exists()
