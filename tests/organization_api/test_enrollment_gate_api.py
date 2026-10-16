"""Confirming an enrollment through the unlock API, for a course whose enrollments are gated."""

import json

import pytest
from django.core import mail
from django.urls import reverse

from django_email_learning.models import (
    ApiKeyScope,
    ContentDelivery,
    DeactivationReason,
    Enrollment,
    EnrollmentConfirmation,
    EnrollmentStatus,
    GateUnlock,
)
from tests.organization_api.conftest import make_key


def url(enrollment_id):
    return reverse("django_email_learning:api_v1:enrollment_unlock", kwargs={"enrollment_id": enrollment_id})


@pytest.fixture()
def update_auth(db):
    return {"HTTP_AUTHORIZATION": f"Bearer {make_key(scopes=[ApiKeyScope.ENROLLMENTS_UPDATE])}"}


@pytest.fixture()
def gated_enrollment(gate_course, enrollment):
    """An unverified enrollment in a course gated by `signup`, which also has a `payment` gate."""
    course = gate_course.course
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "signup"
    course.save()
    return enrollment


def _post(api_client, auth, enrollment_id, **payload):
    return api_client.post(url(enrollment_id), data=json.dumps(payload), content_type="application/json", **auth)


def test_naming_the_enrollment_gate_confirms_the_enrollment(api_client, update_auth, gated_enrollment):
    response = _post(api_client, update_auth, gated_enrollment.id, gate="signup")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unlocked"
    assert body["gate"] == "signup"
    assert body["enrollment"]["status"] == EnrollmentStatus.ACTIVE
    assert body["enrollment"]["waiting_at_gate"] is None
    gated_enrollment.refresh_from_db()
    assert gated_enrollment.status == EnrollmentStatus.ACTIVE
    assert ContentDelivery.objects.filter(enrollment=gated_enrollment).exists()
    assert [email.subject for email in mail.outbox] == ["Enrollment Verified"]


def test_without_a_gate_an_unconfirmed_enrollment_is_confirmed(api_client, update_auth, gated_enrollment):
    response = _post(api_client, update_auth, gated_enrollment.id)

    assert response.status_code == 200
    assert response.json()["gate"] == "signup"


def test_confirming_again_is_reported_and_harmless(api_client, update_auth, gated_enrollment):
    _post(api_client, update_auth, gated_enrollment.id, gate="signup")

    response = _post(api_client, update_auth, gated_enrollment.id, gate="signup")

    assert response.status_code == 200
    assert response.json()["status"] == "already_unlocked"
    assert len(mail.outbox) == 1


def test_an_ended_enrollment_cannot_be_confirmed(api_client, update_auth, gated_enrollment):
    gated_enrollment.status = EnrollmentStatus.DEACTIVATED
    gated_enrollment.deactivation_reason = DeactivationReason.CANCELED
    gated_enrollment.save()

    response = _post(api_client, update_auth, gated_enrollment.id, gate="signup")

    assert response.status_code == 409


def test_a_content_gate_can_still_be_unlocked_before_confirmation(api_client, update_auth, gated_enrollment):
    response = _post(api_client, update_auth, gated_enrollment.id, gate="payment")

    assert response.status_code == 200
    assert response.json()["status"] == "unlocked_in_advance"
    assert GateUnlock.objects.filter(enrollment=gated_enrollment).exists()
    gated_enrollment.refresh_from_db()
    assert gated_enrollment.status == EnrollmentStatus.UNVERIFIED


def test_the_enrollment_gate_key_means_nothing_in_a_course_confirmed_by_link(
    api_client, update_auth, gate_course, enrollment
):
    gate_course.course.enrollment_gate_key = "signup"
    gate_course.course.save()

    response = _post(api_client, update_auth, enrollment.id, gate="signup")

    assert response.status_code == 404
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.UNVERIFIED


def test_an_unconfirmed_enrollment_reports_the_enrollment_gate(api_client, gated_enrollment):
    auth = {"HTTP_AUTHORIZATION": f"Bearer {make_key(scopes=[ApiKeyScope.ENROLLMENTS_CREATE])}"}
    course = gated_enrollment.course
    course.enabled = True
    course.save()

    response = api_client.post(
        reverse("django_email_learning:api_v1:enrollments"),
        data=json.dumps({"email": "new@example.com", "course_slug": course.slug, "verified": False}),
        content_type="application/json",
        **auth,
    )

    assert response.status_code == 201
    assert response.json()["enrollment"]["waiting_at_gate"] == "signup"
    assert Enrollment.objects.get(learner__email="new@example.com").status == EnrollmentStatus.UNVERIFIED
    assert mail.outbox[0].subject.startswith("Complete your enrollment")
