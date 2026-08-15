import json
from unittest import mock

from django.core import mail
from django.urls import reverse

from django_email_learning.models import (
    Enrollment,
    EnrollmentStatus,
    Learner,
    Newsletter,
    NewsletterSubscriber,
)

URL = reverse("django_email_learning:api_v1:enrollments")


def _post(api_client, auth, **payload):
    return api_client.post(URL, data=json.dumps(payload), content_type="application/json", **auth)


def test_enrolling_creates_a_verified_enrollment(api_client, auth, enabled_course):
    """The caller holds a key for the organization and is trusted to have
    established the address, so the enrollment starts active by default."""
    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "enrolled"
    assert body["enrollment"]["email"] == "learner@example.com"
    assert body["enrollment"]["course_slug"] == enabled_course.slug
    assert body["enrollment"]["status"] == EnrollmentStatus.ACTIVE
    assert body["enrollment"]["activated_at"] is not None

    enrollment = Enrollment.objects.get(id=body["enrollment"]["id"])
    assert enrollment.course == enabled_course
    assert enrollment.learner.organization_id == 1


def test_a_verified_enrollment_starts_the_course(api_client, auth, enabled_course, course_lesson_content):
    """Activation is the thing that schedules the first content, so a verified
    enrollment has to leave the learner with a delivery on the way."""
    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)

    enrollment = Enrollment.objects.get(id=response.json()["enrollment"]["id"])
    delivery = enrollment.content_deliveries.get()
    assert delivery.course_content == course_lesson_content
    assert delivery.delivery_schedules.exists()


def test_a_verified_enrollment_is_not_asked_to_verify(api_client, auth, enabled_course):
    """No verification link — the learner gets the confirmation that the course
    has started, which is what activation sends."""
    mail.outbox.clear()
    _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug)

    assert len(mail.outbox) == 1
    assert "learner@example.com" in mail.outbox[0].to
    assert mail.outbox[0].subject == "Enrollment Verified"


def test_verified_false_creates_an_unverified_enrollment(api_client, auth, enabled_course):
    response = _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug, verified=False)

    assert response.status_code == 201
    body = response.json()
    assert body["enrollment"]["status"] == EnrollmentStatus.UNVERIFIED
    assert "activated_at" not in body["enrollment"]

    enrollment = Enrollment.objects.get(id=body["enrollment"]["id"])
    assert not enrollment.content_deliveries.exists()


def test_verified_false_sends_a_verification_email(api_client, auth, enabled_course):
    mail.outbox.clear()
    _post(api_client, auth, email="learner@example.com", course_slug=enabled_course.slug, verified=False)

    assert len(mail.outbox) == 1
    assert "learner@example.com" in mail.outbox[0].to
    assert mail.outbox[0].subject == "Verify your enrollment"


def test_a_verified_enrollment_into_a_course_with_nothing_published_creates_nothing(
    api_client, auth, empty_enabled_course
):
    """Activation cannot schedule a first delivery here, and half of a verified
    enrollment is worse than none: the caller gets a 500 and can retry once the
    course has content, rather than an active row that reads back as already
    enrolled and never receives anything."""
    mail.outbox.clear()
    response = _post(api_client, auth, email="learner@example.com", course_slug=empty_enabled_course.slug)

    assert response.status_code == 500
    assert response.json()["error_id"]
    assert not Enrollment.objects.exists()
    assert mail.outbox == []


def test_a_verified_enrollment_confirms_the_newsletter_subscription(api_client, auth, enabled_course):
    """Subscribing is opt-in at enroll time and confirmed by verification. With
    nobody left to click a link, creating the enrollment verified has to confirm
    it in the same request rather than leave it pending forever."""
    newsletter = Newsletter.objects.create(title="Course Updates", language="en", organization_id=1)
    enabled_course.newsletter = newsletter
    enabled_course.save(update_fields=["newsletter"])

    _post(
        api_client,
        auth,
        email="learner@example.com",
        course_slug=enabled_course.slug,
        subscribe_to_newsletter=True,
    )

    subscriber = NewsletterSubscriber.objects.get(newsletter=newsletter, email="learner@example.com")
    assert subscriber.is_confirmed


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
