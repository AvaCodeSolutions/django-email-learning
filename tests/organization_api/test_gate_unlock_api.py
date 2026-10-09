import json

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ApiKeyScope,
    ContentDelivery,
    Course,
    DeactivationReason,
    Enrollment,
    EnrollmentStatus,
    GateUnlock,
    GateUnlockSource,
    Learner,
)
from django_email_learning.organization_api.serializers import EnrollmentResponse
from tests.organization_api.conftest import make_key


def url(enrollment_id):
    return reverse("django_email_learning:api_v1:enrollment_unlock", kwargs={"enrollment_id": enrollment_id})


@pytest.fixture()
def update_auth(db):
    return {"HTTP_AUTHORIZATION": f"Bearer {make_key(scopes=[ApiKeyScope.ENROLLMENTS_UPDATE])}"}


def _post(api_client, auth, enrollment_id, **payload):
    return api_client.post(url(enrollment_id), data=json.dumps(payload), content_type="application/json", **auth)


def test_unlocking_a_named_gate_moves_a_waiting_learner_on(api_client, update_auth, waiting_enrollment):
    response = _post(api_client, update_auth, waiting_enrollment.id, gate="payment")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unlocked"
    assert body["gate"] == "payment"
    assert body["enrollment"]["id"] == waiting_enrollment.id
    assert body["enrollment"]["waiting_at_gate"] is None
    unlock = GateUnlock.objects.get(enrollment=waiting_enrollment)
    assert unlock.source == GateUnlockSource.API
    assert unlock.api_key is not None
    assert ContentDelivery.objects.filter(
        enrollment=waiting_enrollment, course_content__lesson__title="Paid lesson"
    ).exists()


def test_without_a_gate_the_one_the_learner_waits_at_is_unlocked(api_client, update_auth, waiting_enrollment):
    response = _post(api_client, update_auth, waiting_enrollment.id)

    assert response.status_code == 200
    assert response.json()["gate"] == "payment"


def test_without_a_gate_a_learner_not_waiting_is_refused(api_client, update_auth, gate_course, active_enrollment):
    response = _post(api_client, update_auth, active_enrollment.id)

    assert response.status_code == 409
    assert not GateUnlock.objects.exists()


def test_a_gate_can_be_unlocked_before_the_learner_reaches_it(api_client, update_auth, gate_course, active_enrollment):
    response = _post(api_client, update_auth, active_enrollment.id, gate="payment")

    assert response.status_code == 200
    assert response.json()["status"] == "unlocked_in_advance"


def test_unlocking_again_is_reported_and_harmless(api_client, update_auth, waiting_enrollment):
    _post(api_client, update_auth, waiting_enrollment.id, gate="payment")

    response = _post(api_client, update_auth, waiting_enrollment.id, gate="payment")

    assert response.status_code == 200
    assert response.json()["status"] == "already_unlocked"
    assert GateUnlock.objects.count() == 1


def test_an_enrollment_reports_the_gate_it_waits_at(waiting_enrollment):
    assert EnrollmentResponse.from_django_model(waiting_enrollment).waiting_at_gate == "payment"


def test_an_unknown_gate_is_not_found(api_client, update_auth, waiting_enrollment):
    response = _post(api_client, update_auth, waiting_enrollment.id, gate="unknown")

    assert response.status_code == 404
    assert response.json() == {"error": "Gate not found"}


def test_an_unknown_enrollment_is_not_found(api_client, update_auth, gate_course):
    response = _post(api_client, update_auth, 999999, gate="payment")

    assert response.status_code == 404


def test_another_organizations_enrollment_is_not_found(api_client, update_auth, other_organization):
    other_course = Course.objects.create(title="Other", slug="other", organization=other_organization)
    other_enrollment = Enrollment.objects.create(
        learner=Learner.objects.create(email="someone@example.com", organization=other_organization),
        course=other_course,
        status=EnrollmentStatus.ACTIVE,
    )

    response = _post(api_client, update_auth, other_enrollment.id, gate="payment")

    assert response.status_code == 404


def test_an_ended_enrollment_is_refused(api_client, update_auth, waiting_enrollment):
    waiting_enrollment.status = EnrollmentStatus.DEACTIVATED
    waiting_enrollment.deactivation_reason = DeactivationReason.CANCELED
    waiting_enrollment.save()

    response = _post(api_client, update_auth, waiting_enrollment.id, gate="payment")

    assert response.status_code == 409


def test_a_key_without_the_update_scope_is_forbidden(api_client, auth, waiting_enrollment):
    response = _post(api_client, auth, waiting_enrollment.id, gate="payment")

    assert response.status_code == 403
    assert "enrollments:update" in response.json()["error"]


def test_a_malformed_gate_is_rejected(api_client, update_auth, waiting_enrollment):
    response = _post(api_client, update_auth, waiting_enrollment.id, gate="")

    assert response.status_code == 400
