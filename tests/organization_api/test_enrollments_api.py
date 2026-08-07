import json

from django.core import mail
from django.urls import reverse

from django_email_learning.models import (
    ApiKeyScope,
    Enrollment,
    EnrollmentStatus,
    Learner,
)

from .conftest import make_key

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


def test_write_scope_is_required_to_enroll(api_client, enabled_course, db):
    token = make_key([ApiKeyScope.ENROLLMENTS_READ])
    response = api_client.post(
        URL,
        data=json.dumps({"email": "learner@example.com", "course_slug": enabled_course.slug}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 403
    assert not Enrollment.objects.exists()


def test_listing_enrollments(api_client, auth, enabled_course):
    _post(api_client, auth, email="a@example.com", course_slug=enabled_course.slug)
    _post(api_client, auth, email="b@example.com", course_slug=enabled_course.slug)

    response = api_client.get(URL, **auth)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {e["email"] for e in body["enrollments"]} == {"a@example.com", "b@example.com"}


def test_listing_filters_by_email_and_course(api_client, auth, enabled_course):
    _post(api_client, auth, email="a@example.com", course_slug=enabled_course.slug)
    _post(api_client, auth, email="b@example.com", course_slug=enabled_course.slug)

    body = api_client.get(URL, {"email": "a@example.com"}, **auth).json()
    assert body["total"] == 1
    assert body["enrollments"][0]["email"] == "a@example.com"

    body = api_client.get(URL, {"course_slug": "no-such-course"}, **auth).json()
    assert body["total"] == 0


def test_listing_rejects_an_unknown_status(api_client, auth, enabled_course):
    assert api_client.get(URL, {"status": "banished"}, **auth).status_code == 400


def test_listing_caps_the_page_size(api_client, auth, enabled_course):
    assert api_client.get(URL, {"limit": "5000"}, **auth).status_code == 400


def test_listing_paginates(api_client, auth, enabled_course):
    for i in range(3):
        _post(api_client, auth, email=f"learner{i}@example.com", course_slug=enabled_course.slug)

    body = api_client.get(URL, {"limit": 2, "offset": 0}, **auth).json()
    assert body["total"] == 3
    assert len(body["enrollments"]) == 2

    body = api_client.get(URL, {"limit": 2, "offset": 2}, **auth).json()
    assert len(body["enrollments"]) == 1


def test_listing_excludes_other_organizations_enrollments(api_client, auth, enabled_course, other_organization_course):
    other_learner = Learner(email="elsewhere@example.com", organization=other_organization_course.organization)
    other_learner.save()
    Enrollment.objects.create(learner=other_learner, course=other_organization_course)
    _post(api_client, auth, email="ours@example.com", course_slug=enabled_course.slug)

    body = api_client.get(URL, **auth).json()
    assert body["total"] == 1
    assert body["enrollments"][0]["email"] == "ours@example.com"


def test_read_scope_is_required_to_list(api_client, enabled_course, db):
    token = make_key([ApiKeyScope.ENROLLMENTS_WRITE])
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 403
