"""Authoring a gate over the platform API, and seeing and unlocking waiting learners."""

import json

import pytest
from django.urls import reverse

from django_email_learning.models import (
    CourseContent,
    Enrollment,
    EnrollmentStatus,
    Gate,
    GateUnlock,
    GateUnlockSource,
    Learner,
)


def contents_url(course):
    return reverse(
        "django_email_learning:api_platform:course_contents_reorder",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    ).removesuffix("reorder/")


def content_url(content):
    return f"{contents_url(content.course)}{content.id}/"


def unlock_url(enrollment, content):
    return reverse(
        "django_email_learning:api_platform:enrollment_gate_unlock",
        kwargs={
            "organization_id": enrollment.course.organization_id,
            "enrollment_id": enrollment.id,
            "course_content_id": content.id,
        },
    )


def enrollment_url(enrollment):
    return reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": enrollment.course.organization_id, "enrollment_id": enrollment.id},
    )


def post_json(client, url, data):
    return client.post(url, data=json.dumps(data), content_type="application/json")


def new_gate(**overrides):
    return {
        "waiting_period": {"period": 1, "type": "hours"},
        "content": {
            "type": "gate",
            "title": "Payment",
            "key": "payment",
            "message": "<p>Pay here</p>",
            "timeout_days": 14,
            "timeout_action": "continue",
            **overrides,
        },
    }


# ── authoring ────────────────────────────────────────────────────────────────


def test_creating_a_gate(editor_client, course):
    response = post_json(editor_client, contents_url(course), new_gate())

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "gate"
    assert body["gate"] == {
        "id": body["gate"]["id"],
        "title": "Payment",
        "key": "payment",
        "message": "<p>Pay here</p>",
        "timeout_days": 14,
        "timeout_action": "continue",
    }


def test_a_gate_message_is_sanitized(editor_client, course):
    response = post_json(editor_client, contents_url(course), new_gate(message="<p>Hi</p><script>alert(1)</script>"))

    assert "<script>" not in response.json()["gate"]["message"]


@pytest.mark.parametrize("key", ["", "has space", "slash/es"])
def test_a_gate_key_must_be_a_slug(editor_client, course, key):
    response = post_json(editor_client, contents_url(course), new_gate(key=key))

    assert response.status_code == 400
    assert not Gate.objects.exists()


def test_a_gate_key_is_unique_within_a_course(editor_client, gate_course):
    response = post_json(editor_client, contents_url(gate_course.course), new_gate(title="Second"))

    assert response.status_code == 400
    # The refused gate is not left behind.
    assert Gate.objects.count() == 1


def test_updating_a_gate(editor_client, gate_course):
    response = post_json(
        editor_client,
        content_url(gate_course.gate_content),
        {"gate": {"title": "Account", "key": "account", "timeout_days": 3, "timeout_action": "deactivate"}},
    )

    assert response.status_code == 200
    gate_course.gate.refresh_from_db()
    assert (gate_course.gate.title, gate_course.gate.key, gate_course.gate.timeout_days) == ("Account", "account", 3)


def test_updating_a_gate_to_a_key_already_used_is_refused(editor_client, gate_course):
    second = CourseContent.objects.create(
        course=gate_course.course,
        priority=4,
        type="gate",
        gate=Gate.objects.create(title="Account", key="account"),
        waiting_period=3600,
    )

    response = post_json(editor_client, content_url(second), {"gate": {"key": "payment"}})

    assert response.status_code == 409
    second.gate.refresh_from_db()
    assert second.gate.key == "account"


def test_the_content_list_shows_each_gates_key(editor_client, gate_course):
    response = editor_client.get(contents_url(gate_course.course))

    gate_row = next(row for row in response.json()["course_contents"] if row["type"] == "gate")
    assert gate_row["gate_key"] == "payment"
    assert gate_row["title"] == "Payment"


# ── waiting learners ─────────────────────────────────────────────────────────


def test_an_enrollment_shows_the_gate_it_waits_at(org_admin_client, gate_course, waiting_enrollment):
    response = org_admin_client.get(enrollment_url(waiting_enrollment))

    body = response.json()
    assert body["status"] == "active"
    assert body["waiting_at_gate"]["key"] == "payment"
    assert body["waiting_at_gate"]["course_content_id"] == gate_course.gate_content.id
    assert any(
        event["type"] == "content_sent" and event["event_data"]["course_content_type"] == "gate"
        for event in body["events"]
    )


def test_an_admin_can_unlock_a_waiting_learner(org_admin_client, gate_course, waiting_enrollment, users):
    response = org_admin_client.post(unlock_url(waiting_enrollment, gate_course.gate_content))

    assert response.status_code == 200
    assert response.json()["status"] == "unlocked"
    unlock = GateUnlock.objects.get(enrollment=waiting_enrollment)
    assert unlock.source == GateUnlockSource.ADMIN
    assert unlock.unlocked_by is not None

    body = org_admin_client.get(enrollment_url(waiting_enrollment)).json()
    assert body["waiting_at_gate"] is None
    [event] = [event for event in body["events"] if event["type"] == "gate_unlocked"]
    assert event["event_data"]["gate_title"] == "Payment"
    assert event["event_data"]["source"] == "admin"


def test_only_an_admin_can_unlock(instructor_client, gate_course, waiting_enrollment):
    response = instructor_client.post(unlock_url(waiting_enrollment, gate_course.gate_content))

    assert response.status_code == 403
    assert not GateUnlock.objects.exists()


def test_unlocking_content_that_is_not_a_gate_is_not_found(org_admin_client, gate_course, waiting_enrollment):
    response = org_admin_client.post(unlock_url(waiting_enrollment, gate_course.welcome))

    assert response.status_code == 404


def test_learners_can_be_filtered_to_those_waiting(org_admin_client, gate_course, waiting_enrollment):
    progressing = Learner.objects.create(email="progressing@example.com", organization_id=1)
    Enrollment.objects.create(learner=progressing, course=gate_course.course, status=EnrollmentStatus.ACTIVE)
    url = reverse("django_email_learning:api_platform:learners_list", kwargs={"organization_id": 1})

    response = org_admin_client.get(f"{url}?status=waiting&course_id={gate_course.course.id}")

    [item] = response.json()["items"]
    assert item["email"] == waiting_enrollment.learner.email
    assert item["enrollment_waiting_at_gate"] == "Payment"
