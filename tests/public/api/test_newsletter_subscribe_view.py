import pytest
from django.urls import reverse

from django_email_learning.models import Newsletter, NewsletterSubscriber


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Tips", language="en", organization_id=1)


@pytest.fixture()
def newsletter_2(db):
    return Newsletter.objects.create(title="Monthly Digest", language="en", organization_id=1)


def subscribe_url(organization_id=1):
    return reverse(
        "django_email_learning:api_public:newsletter_subscribe",
        kwargs={"organization_id": organization_id},
    )


def test_subscribe_creates_subscriber(db, anonymous_client, newsletter):
    response = anonymous_client.post(
        subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "subscribed"
    assert NewsletterSubscriber.objects.filter(newsletter=newsletter, email="user@example.com").exists()


def test_subscribe_to_multiple_newsletters(db, anonymous_client, newsletter, newsletter_2):
    response = anonymous_client.post(
        subscribe_url(),
        data={
            "email": "user@example.com",
            "newsletter_ids": [newsletter.id, newsletter_2.id],
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert NewsletterSubscriber.objects.filter(email="user@example.com").count() == 2


def test_subscribe_is_idempotent(db, anonymous_client, newsletter):
    for _ in range(2):
        response = anonymous_client.post(
            subscribe_url(),
            data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
            content_type="application/json",
        )
        assert response.status_code == 200

    assert NewsletterSubscriber.objects.filter(newsletter=newsletter, email="user@example.com").count() == 1


def test_subscribe_invalid_email_returns_400(db, anonymous_client, newsletter):
    response = anonymous_client.post(
        subscribe_url(),
        data={"email": "not-an-email", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_subscribe_empty_newsletter_ids_returns_400(db, anonymous_client, newsletter):
    response = anonymous_client.post(
        subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": []},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_subscribe_newsletter_from_other_org_returns_400(db, anonymous_client, newsletter):
    response = anonymous_client.post(
        subscribe_url(organization_id=999),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_subscribe_nonexistent_newsletter_id_returns_400(db, anonymous_client):
    response = anonymous_client.post(
        subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": [99999]},
        content_type="application/json",
    )
    assert response.status_code == 400
