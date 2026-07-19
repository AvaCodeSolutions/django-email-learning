import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from django_email_learning.models import Newsletter, NewsletterSubscriber


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Tips", language="en", organization_id=1)


def embed_subscribe_url(organization_id=1):
    return reverse(
        "django_email_learning:api_public:embed_newsletter_subscribe",
        kwargs={"organization_id": organization_id},
    )


def test_embed_subscribe_disabled_by_default(anonymous_client, newsletter, settings):
    assert not settings.DJANGO_EMAIL_LEARNING.get("EMBEDDABLE_ENROLLMENT_ENABLED")

    response = anonymous_client.post(
        embed_subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 404
    assert not NewsletterSubscriber.objects.filter(newsletter=newsletter).exists()


def test_embed_subscribe_creates_subscriber_when_enabled(anonymous_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.post(
        embed_subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert NewsletterSubscriber.objects.filter(newsletter=newsletter, email="user@example.com").exists()


def test_embed_subscribe_does_not_require_csrf_token(newsletter, settings):
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = csrf_enforcing_client.post(
        embed_subscribe_url(),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_embed_subscribe_rate_limits_by_email_when_enabled(db, anonymous_client, settings):
    cache.clear()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    responses = []
    for i in range(6):
        newsletter = Newsletter.objects.create(title=f"Newsletter {i}", language="en", organization_id=1)
        responses.append(
            anonymous_client.post(
                embed_subscribe_url(),
                data={"email": "same-user@example.com", "newsletter_ids": [newsletter.id]},
                content_type="application/json",
            )
        )

    assert responses[-1].status_code == 429
    assert sum(1 for r in responses if r.status_code == 429) == 1
