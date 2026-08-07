import json
from unittest import mock

from django.core import mail
from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner

URL = reverse("django_email_learning:api_v1:enrollments")


def _post(api_client, auth, **payload):
    return api_client.post(URL, data=json.dumps(payload), content_type="application/json", **auth)


def test_enrolling_creates_an_unverified_enrollment(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "enrolled"
    assert body["enrollment"]["email"] == "learner@example.com"
    assert body["enrollment"]["course_slug"] == enabled_course.slug
    assert body["enrollment"]["status"] == EnrollmentStatus.UNVERIFIED

    enrollment = Enrollment.objects.get(id=body["enrollment"]["id"])
    assert enrollment.course == enabled_course
    assert enrollment.learner.organization_id == 1


def test_enrolling_sends_a_verification_email(api_client, auth, enabled_course):
    mail.outbox.clear()
    _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)
    assert len(mail.outbox) == 1
    assert "learner@example.com" in mail.outbox[0].to


def test_email_is_normalized_to_lowercase(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="Learner@Example.COM", course_slug=enabled_course.slug)
    assert response.status_code == 201
    assert response.json()["enrollment"]["email"] == "learner@example.com"
    assert Learner.objects.filter(email="learner@example.com", organization_id=1).exists()


def test_enrolling_twice_reports_already_enrolled(api_client, auth, enabled_course):
    _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)
    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)

    assert response.status_code == 200
    assert response.json() == {"status": "already_enrolled"}
    assert Enrollment.objects.count() == 1


def test_enrolling_in_an_unknown_course_returns_404(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="learner@example.com", course_slug="no-such-course")
    assert response.status_code == 404


def test_enrolling_in_a_disabled_course_returns_404(api_client, auth, course):
    """The course exists and belongs to the organization, but EnrollCommand
    only accepts enabled courses."""
    assert course.enabled is False
    response = _post(api_client, auth, email="learner@example.com", course_slug=course.slug)
    assert response.status_code == 404


def test_enrolling_in_a_private_course_is_allowed(api_client, auth, enabled_course):
    """Unlike the embeddable public endpoint, an authenticated organization key
    may enrol into its own non-public courses."""
    enabled_course.is_public = False
    enabled_course.save()

    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)
    assert response.status_code == 201


def test_cannot_enroll_into_another_organizations_course(api_client, auth, other_organization_course):
    """The course slug is resolved against the key's organization, so naming
    another organization's course reads as 'not found' rather than reaching it."""
    response = _post(api_client, auth, email="learner@example.com", course_slug=other_organization_course.slug)
    assert response.status_code == 404
    assert not Enrollment.objects.exists()


def test_blocked_email_is_rejected(api_client, auth, enabled_course, blocked_email):
    response = _post(api_client, auth, email=blocked_email.email, course_slug=enabled_course.slug)
    assert response.status_code == 403
    assert response.json()["error"] == "Email is blocked"


def test_invalid_email_is_rejected(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="not-an-email", course_slug=enabled_course.slug)
    assert response.status_code == 400


def test_missing_course_slug_is_rejected(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="learner@example.com")
    assert response.status_code == 400


def test_malformed_json_is_rejected(api_client, auth, enabled_course):
    response = api_client.post(URL, data="{not json", content_type="application/json", **auth)
    assert response.status_code == 400


def test_rate_limit_returns_429(api_client, auth, enabled_course):
    with mock.patch(
        "django_email_learning.organization_api.views.get_rate_limit_settings",
        return_value={"PER_KEY_LIMIT": 2, "PER_KEY_WINDOW_SECONDS": 60},
    ):
        assert _post(api_client, auth, email="a@example.com", course_slug=enabled_course.slug).status_code == 201
        assert _post(api_client, auth, email="b@example.com", course_slug=enabled_course.slug).status_code == 201
        response = _post(api_client, auth, email="c@example.com", course_slug=enabled_course.slug)

    assert response.status_code == 429
    assert response.json()["error"] == "Too many requests. Please try again later."


def test_rate_limit_is_per_key(api_client, auth, enabled_course, db):
    """Budgets are keyed on key_id, so one caller exhausting its allowance
    can't lock out another key on the same organization."""
    from .conftest import make_key

    other_auth = {"HTTP_AUTHORIZATION": f"Bearer {make_key()}"}

    with mock.patch(
        "django_email_learning.organization_api.views.get_rate_limit_settings",
        return_value={"PER_KEY_LIMIT": 1, "PER_KEY_WINDOW_SECONDS": 60},
    ):
        assert _post(api_client, auth, email="a@example.com", course_slug=enabled_course.slug).status_code == 201
        assert _post(api_client, auth, email="b@example.com", course_slug=enabled_course.slug).status_code == 429
        assert _post(api_client, other_auth, email="c@example.com", course_slug=enabled_course.slug).status_code == 201
