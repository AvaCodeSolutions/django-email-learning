import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from django_email_learning.models import Newsletter, NewsletterSubscriber, Organization


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Tips", language="en", organization_id=1)


@pytest.fixture()
def embed_token(db) -> str:
    organization = Organization.objects.get(id=1)
    organization.embed_token = Organization.generate_embed_token()
    organization.save(update_fields=["embed_token"])
    return organization.embed_token


def embed_subscribe_url(token: str) -> str:
    return reverse("django_email_learning:api_public:embed_newsletter_subscribe", kwargs={"token": token})


def test_embed_subscribe_disabled_by_default(anonymous_client, newsletter, embed_token, settings):
    assert not settings.DJANGO_EMAIL_LEARNING.get("EMBEDDABLE_ENROLLMENT_ENABLED")

    response = anonymous_client.post(
        embed_subscribe_url(embed_token),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 404
    assert not NewsletterSubscriber.objects.filter(newsletter=newsletter).exists()


def test_embed_subscribe_invalid_token_returns_404_when_enabled(anonymous_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.post(
        embed_subscribe_url("not-a-real-token"),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 404
    assert not NewsletterSubscriber.objects.filter(newsletter=newsletter).exists()


def test_embed_subscribe_creates_subscriber_when_enabled(anonymous_client, newsletter, embed_token, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.post(
        embed_subscribe_url(embed_token),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    assert NewsletterSubscriber.objects.filter(newsletter=newsletter, email="user@example.com").exists()


def test_embed_subscribe_invalid_json_returns_400(anonymous_client, embed_token, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.post(embed_subscribe_url(embed_token), data="not-json", content_type="application/json")
    assert response.status_code == 400


def test_embed_subscribe_does_not_require_csrf_token(newsletter, embed_token, settings):
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = csrf_enforcing_client.post(
        embed_subscribe_url(embed_token),
        data={"email": "user@example.com", "newsletter_ids": [newsletter.id]},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_embed_subscribe_rate_limits_by_email_when_enabled(db, anonymous_client, embed_token, settings):
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
                embed_subscribe_url(embed_token),
                data={"email": "same-user@example.com", "newsletter_ids": [newsletter.id]},
                content_type="application/json",
            )
        )

    assert responses[-1].status_code == 429
    assert sum(1 for r in responses if r.status_code == 429) == 1


def test_embed_subscribe_rate_limits_by_token_isolated_per_organization(db, anonymous_client, embed_token, settings):
    cache.clear()
    other_organization = Organization.objects.create(name="Other Org", embed_token=Organization.generate_embed_token())
    other_newsletter = Newsletter.objects.create(
        title="Other Org Newsletter", language="en", organization=other_organization
    )
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
        "EMBEDDABLE_ENROLLMENT_RATE_LIMITS": {
            "PER_TOKEN_LIMIT": 1,
            "PER_TOKEN_WINDOW_SECONDS": 300,
        },
    }
    newsletter_a = Newsletter.objects.create(title="Org A Newsletter", language="en", organization_id=1)

    first = anonymous_client.post(
        embed_subscribe_url(embed_token),
        data={"email": "a1@example.com", "newsletter_ids": [newsletter_a.id]},
        content_type="application/json",
    )
    exhausted = anonymous_client.post(
        embed_subscribe_url(embed_token),
        data={"email": "a2@example.com", "newsletter_ids": [newsletter_a.id]},
        content_type="application/json",
    )
    assert first.status_code == 200
    assert exhausted.status_code == 429

    other_response = anonymous_client.post(
        embed_subscribe_url(other_organization.embed_token),
        data={"email": "b1@example.com", "newsletter_ids": [other_newsletter.id]},
        content_type="application/json",
    )
    assert other_response.status_code == 200
