import json
from datetime import timedelta

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


def list_url(organization_id: int, newsletter_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:sendouts_list",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter_id},
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


# --- CREATE / UPDATE sanitization ---


def test_create_sendout_strips_script_but_keeps_allowed_formatting(superadmin_client, newsletter):
    payload = {
        "subject": "Weekly update",
        "body": "<p>Hello <strong>world</strong></p><script>alert(document.cookie)</script>",
        "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
    }
    response = superadmin_client.post(list_url(1, newsletter.id), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    # SendoutResponse (returned on create) doesn't include body — check the stored value.
    body = Sendout.objects.get(id=response.json()["id"]).body
    assert "<script>" not in body
    assert "<strong>world</strong>" in body


def test_update_sendout_strips_script_tag(superadmin_client, scheduled_sendout):
    payload = {
        "subject": scheduled_sendout.subject,
        "body": '<p>Updated</p><img src=x onerror="alert(1)">',
        "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
    }
    url = detail_url(1, scheduled_sendout.newsletter_id, scheduled_sendout.id)
    response = superadmin_client.patch(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    assert "onerror" not in response.json()["body"]


# --- CREATE / UPDATE scheduled_at validation ---


def test_create_sendout_in_past_returns_400(superadmin_client, newsletter):
    payload = {
        "subject": "Too late",
        "body": "<p>Body</p>",
        "scheduled_at": (timezone.now() - timedelta(minutes=5)).isoformat(),
    }
    response = superadmin_client.post(list_url(1, newsletter.id), json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert response.json()["error"] == "Scheduled date must be in the future."
    assert not Sendout.objects.filter(newsletter=newsletter).exists()


def test_create_sendout_in_past_without_timezone_returns_400(superadmin_client, newsletter):
    payload = {
        "subject": "Too late",
        "body": "<p>Body</p>",
        "scheduled_at": "2000-01-01T10:00:00",
    }
    response = superadmin_client.post(list_url(1, newsletter.id), json.dumps(payload), content_type="application/json")
    assert response.status_code == 400


def test_update_sendout_to_past_returns_400(superadmin_client, scheduled_sendout):
    payload = {
        "subject": scheduled_sendout.subject,
        "body": scheduled_sendout.body,
        "scheduled_at": (timezone.now() - timedelta(days=1)).isoformat(),
    }
    url = detail_url(1, scheduled_sendout.newsletter_id, scheduled_sendout.id)
    response = superadmin_client.patch(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    scheduled_sendout.refresh_from_db()
    assert scheduled_sendout.scheduled_at > timezone.now() - timedelta(hours=1)


def test_update_sendout_keeping_existing_past_date_succeeds(superadmin_client, newsletter):
    past = timezone.now() - timedelta(days=1)
    sendout = Sendout.objects.create(
        newsletter=newsletter,
        subject="Blocked",
        body="Body",
        scheduled_at=past,
        status=Sendout.Status.BLOCKED,
    )
    payload = {"subject": "Fixed subject", "body": "<p>Body</p>", "scheduled_at": past.isoformat()}
    url = detail_url(1, newsletter.id, sendout.id)
    response = superadmin_client.patch(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    assert response.json()["subject"] == "Fixed subject"


# --- Skipped sendouts ---


@pytest.fixture()
def skipped_sendout(newsletter):
    return Sendout.objects.create(
        newsletter=newsletter,
        subject="Nobody to send to",
        body="Body",
        scheduled_at=timezone.now() - timedelta(hours=1),
        status=Sendout.Status.SKIPPED,
        skipped_reason=Sendout.SkippedReason.NO_CONFIRMED_SUBSCRIBERS,
    )


def test_list_skipped_sendouts_includes_reason(superadmin_client, newsletter, skipped_sendout, scheduled_sendout):
    response = superadmin_client.get(list_url(1, newsletter.id), {"status": "skipped"})
    assert response.status_code == 200
    sendouts = response.json()["sendouts"]
    assert [s["id"] for s in sendouts] == [skipped_sendout.id]
    assert sendouts[0]["status"] == "skipped"
    assert sendouts[0]["skipped_reason"] == "no_confirmed_subscribers"


def test_update_skipped_sendout_returns_409(superadmin_client, skipped_sendout):
    payload = {
        "subject": "New subject",
        "body": "<p>Body</p>",
        "scheduled_at": (timezone.now() + timedelta(hours=1)).isoformat(),
    }
    url = detail_url(1, skipped_sendout.newsletter_id, skipped_sendout.id)
    response = superadmin_client.patch(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 409
    skipped_sendout.refresh_from_db()
    assert skipped_sendout.subject == "Nobody to send to"


def test_delete_skipped_sendout_returns_409(superadmin_client, skipped_sendout):
    url = detail_url(1, skipped_sendout.newsletter_id, skipped_sendout.id)
    response = superadmin_client.delete(url)
    assert response.status_code == 409
    assert Sendout.objects.filter(id=skipped_sendout.id).exists()
