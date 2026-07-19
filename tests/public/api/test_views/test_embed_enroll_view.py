from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from django_email_learning.models import Enrollment

URL = reverse("django_email_learning:api_public:embed_enroll")


def test_embed_enroll_view_disabled_by_default(anonymous_client, course, settings):
    course.enabled = True
    course.save()
    assert not settings.DJANGO_EMAIL_LEARNING.get("EMBEDDABLE_ENROLLMENT_ENABLED")

    payload = {
        "organization_id": course.organization_id,
        "email": "test@example.com",
        "course_slug": course.slug,
    }
    response = anonymous_client.post(URL, data=payload, content_type="application/json")
    assert response.status_code == 404
    assert not Enrollment.objects.filter(course=course).exists()


def test_embed_enroll_view_disabled_rejects_preflight(anonymous_client, settings):
    response = anonymous_client.options(URL, HTTP_ORIGIN="https://third-party.example")
    assert response.status_code == 404


def test_embed_enroll_view_creates_enrollment_when_enabled(anonymous_client, course, settings):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {
        "organization_id": course.organization_id,
        "email": "test@example.com",
        "course_slug": course.slug,
    }
    response = anonymous_client.post(
        URL,
        data=payload,
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200
    assert Enrollment.objects.filter(learner__email="test@example.com", course=course).exists()
    assert response["Access-Control-Allow-Origin"] == "*"


def test_embed_enroll_view_preflight_when_enabled(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.options(URL, HTTP_ORIGIN="https://third-party.example")
    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "*"
    assert "POST" in response["Access-Control-Allow-Methods"]


def test_embed_enroll_view_does_not_require_csrf_token(course, settings):
    # A CSRF-enforcing client mirrors a real cross-origin browser request that
    # never had a first-party CSRF cookie to begin with.
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {
        "organization_id": course.organization_id,
        "email": "test@example.com",
        "course_slug": course.slug,
    }
    response = csrf_enforcing_client.post(
        URL,
        data=payload,
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200


def test_embed_enroll_view_rate_limits_by_ip_when_enabled(anonymous_client, course, settings):
    cache.clear()
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    responses = []
    for i in range(21):
        payload = {
            "organization_id": course.organization_id,
            "email": f"test{i}@example.com",
            "course_slug": course.slug,
        }
        responses.append(anonymous_client.post(URL, data=payload, content_type="application/json"))

    assert responses[-1].status_code == 429
    assert sum(1 for r in responses if r.status_code == 429) == 1


def test_embed_enroll_view_honours_configured_rate_limits(anonymous_client, course, settings):
    cache.clear()
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
        "EMBEDDABLE_ENROLLMENT_RATE_LIMITS": {
            "PER_IP_LIMIT": 2,
            "PER_IP_WINDOW_SECONDS": 300,
        },
    }

    responses = []
    for i in range(3):
        payload = {
            "organization_id": course.organization_id,
            "email": f"configured{i}@example.com",
            "course_slug": course.slug,
        }
        responses.append(anonymous_client.post(URL, data=payload, content_type="application/json"))

    assert [r.status_code for r in responses] == [200, 200, 429]
