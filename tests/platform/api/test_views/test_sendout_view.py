import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import Newsletter, Sendout


def detail_url(organization_id: int, newsletter_id: int, sendout_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:sendouts_detail",
        kwargs={
            "organization_id": organization_id,
            "newsletter_id": newsletter_id,
            "sendout_id": sendout_id,
        },
    )


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


@pytest.fixture()
def scheduled_sendout(newsletter):
    return Sendout.objects.create(
        newsletter=newsletter,
        subject="Hello",
        body="Body",
        scheduled_at=timezone.now(),
        status=Sendout.Status.SCHEDULED,
    )


@pytest.fixture()
def sent_sendout(newsletter):
    return Sendout.objects.create(
        newsletter=newsletter,
        subject="Already Sent",
        body="Body",
        scheduled_at=timezone.now(),
        sent_at=timezone.now(),
        status=Sendout.Status.SENT,
    )


# --- DELETE ---


def test_delete_sendout_success(superadmin_client, scheduled_sendout):
    url = detail_url(1, scheduled_sendout.newsletter_id, scheduled_sendout.id)
    response = superadmin_client.delete(url)
    assert response.status_code == 204
    assert not Sendout.objects.filter(id=scheduled_sendout.id).exists()


def test_delete_sendout_not_found(superadmin_client, newsletter):
    url = detail_url(1, newsletter.id, 99999)
    response = superadmin_client.delete(url)
    assert response.status_code == 404


def test_delete_sent_sendout_returns_409(superadmin_client, sent_sendout):
    url = detail_url(1, sent_sendout.newsletter_id, sent_sendout.id)
    response = superadmin_client.delete(url)
    assert response.status_code == 409
    assert Sendout.objects.filter(id=sent_sendout.id).exists()


def test_delete_sendout_requires_admin(viewer_client, scheduled_sendout):
    url = detail_url(1, scheduled_sendout.newsletter_id, scheduled_sendout.id)
    response = viewer_client.delete(url)
    assert response.status_code == 403
    assert Sendout.objects.filter(id=scheduled_sendout.id).exists()


def test_delete_sendout_unauthenticated(anonymous_client, scheduled_sendout):
    url = detail_url(1, scheduled_sendout.newsletter_id, scheduled_sendout.id)
    response = anonymous_client.delete(url)
    assert response.status_code == 401
