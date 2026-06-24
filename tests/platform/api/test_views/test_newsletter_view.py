import json
import pytest
from django.urls import reverse

from django_email_learning.models import Newsletter, NewsletterSubscriber


def get_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:newsletters_list",
        kwargs={"organization_id": organization_id},
    )


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(
        title="Weekly Digest", language="en", organization_id=1
    )


# --- GET ---


def test_list_newsletters_unauthenticated(anonymous_client):
    response = anonymous_client.get(get_url(1))
    assert response.status_code == 401


def test_list_newsletters_empty(superadmin_client):
    response = superadmin_client.get(get_url(1))
    assert response.status_code == 200
    assert response.json()["newsletters"] == []


def test_list_newsletters_returns_data(superadmin_client, newsletter):
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="a@example.com")
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="b@example.com")

    response = superadmin_client.get(get_url(1))
    assert response.status_code == 200
    newsletters = response.json()["newsletters"]
    assert len(newsletters) == 1
    nl = newsletters[0]
    assert nl["title"] == "Weekly Digest"
    assert nl["language"] == "en"
    assert nl["organization_id"] == 1
    assert nl["subscriber_count"] == 2
    assert "id" in nl


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 200), ("platform_admin", 200), ("viewer", 200)],
    indirect=["client"],
)
def test_list_newsletters_role_access(client, expected_status, newsletter):
    response = client.get(get_url(1))
    assert response.status_code == expected_status


# --- POST ---


def test_create_newsletter_success(superadmin_client):
    payload = {"title": "Monthly News", "language": "en"}
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Monthly News"
    assert data["language"] == "en"
    assert data["organization_id"] == 1
    assert data["subscriber_count"] == 0
    assert "id" in data


def test_create_newsletter_unauthenticated(anonymous_client):
    payload = {"title": "News", "language": "en"}
    response = anonymous_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 403), ("viewer", 403), ("platform_admin", 201)],
    indirect=["client"],
)
def test_create_newsletter_role_access(client, expected_status):
    import uuid

    payload = {"title": uuid.uuid4().hex, "language": "en"}
    response = client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == expected_status


def test_create_newsletter_duplicate_title(superadmin_client, newsletter):
    payload = {"title": newsletter.title, "language": "fr"}
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 409


def test_create_newsletter_missing_title(superadmin_client):
    payload = {"language": "en"}
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400


def test_create_newsletter_empty_title(superadmin_client):
    payload = {"title": "", "language": "en"}
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400


# --- DELETE ---


def get_detail_url(organization_id: int, newsletter_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:newsletters_detail",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter_id},
    )


def test_delete_newsletter_success(superadmin_client, newsletter):
    response = superadmin_client.delete(get_detail_url(1, newsletter.id))
    assert response.status_code == 204
    assert not Newsletter.objects.filter(pk=newsletter.pk).exists()


def test_delete_newsletter_unauthenticated(anonymous_client, newsletter):
    response = anonymous_client.delete(get_detail_url(1, newsletter.id))
    assert response.status_code == 401


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 403), ("viewer", 403), ("platform_admin", 204)],
    indirect=["client"],
)
def test_delete_newsletter_role_access(client, expected_status, newsletter):
    response = client.delete(get_detail_url(1, newsletter.id))
    assert response.status_code == expected_status


def test_delete_newsletter_not_found(superadmin_client):
    response = superadmin_client.delete(get_detail_url(1, 99999))
    assert response.status_code == 404


def test_delete_newsletter_wrong_org(superadmin_client, newsletter):
    response = superadmin_client.delete(get_detail_url(999, newsletter.id))
    assert response.status_code == 404
