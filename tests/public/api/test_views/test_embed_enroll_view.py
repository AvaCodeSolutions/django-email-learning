import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from django_email_learning.models import Course, Enrollment, Organization


@pytest.fixture()
def embed_token(course) -> str:
    organization = Organization.objects.get(id=course.organization_id)
    organization.embed_token = Organization.generate_embed_token()
    organization.save(update_fields=["embed_token"])
    return organization.embed_token


def embed_enroll_url(token: str) -> str:
    return reverse("django_email_learning:api_public:embed_enroll", kwargs={"token": token})


def test_embed_enroll_view_disabled_by_default(anonymous_client, course, embed_token, settings):
    course.enabled = True
    course.save()
    assert not settings.DJANGO_EMAIL_LEARNING.get("EMBEDDABLE_ENROLLMENT_ENABLED")

    payload = {"email": "test@example.com", "course_slug": course.slug}
    response = anonymous_client.post(embed_enroll_url(embed_token), data=payload, content_type="application/json")
    assert response.status_code == 404
    assert not Enrollment.objects.filter(course=course).exists()


def test_embed_enroll_view_disabled_rejects_preflight(anonymous_client, embed_token):
    response = anonymous_client.options(embed_enroll_url(embed_token), HTTP_ORIGIN="https://third-party.example")
    assert response.status_code == 404


def test_embed_enroll_view_invalid_token_returns_404_when_enabled(anonymous_client, course, settings):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {"email": "test@example.com", "course_slug": course.slug}
    response = anonymous_client.post(
        embed_enroll_url("not-a-real-token"), data=payload, content_type="application/json"
    )
    assert response.status_code == 404
    assert not Enrollment.objects.filter(course=course).exists()


def test_embed_enroll_view_creates_enrollment_when_enabled(anonymous_client, course, embed_token, settings):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {"email": "test@example.com", "course_slug": course.slug}
    response = anonymous_client.post(
        embed_enroll_url(embed_token),
        data=payload,
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200
    assert Enrollment.objects.filter(learner__email="test@example.com", course=course).exists()
    assert response["Access-Control-Allow-Origin"] == "*"


def test_embed_enroll_view_ignores_organization_id_in_body(anonymous_client, course, embed_token, settings):
    # organization_id is no longer part of the embed request shape - it's derived
    # from the token - so a stray value in the payload must not override that.
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {"email": "test@example.com", "course_slug": course.slug, "organization_id": 999999}
    response = anonymous_client.post(embed_enroll_url(embed_token), data=payload, content_type="application/json")
    assert response.status_code == 200
    assert Enrollment.objects.filter(learner__email="test@example.com", course=course).exists()


def test_embed_enroll_view_invalid_json_returns_400(anonymous_client, embed_token, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.post(embed_enroll_url(embed_token), data="not-json", content_type="application/json")
    assert response.status_code == 400


def test_embed_enroll_view_preflight_when_enabled(anonymous_client, embed_token, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    response = anonymous_client.options(embed_enroll_url(embed_token), HTTP_ORIGIN="https://third-party.example")
    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "*"
    assert "POST" in response["Access-Control-Allow-Methods"]


def test_embed_enroll_view_does_not_require_csrf_token(course, embed_token, settings):
    # A CSRF-enforcing client mirrors a real cross-origin browser request that
    # never had a first-party CSRF cookie to begin with.
    csrf_enforcing_client = Client(enforce_csrf_checks=True)
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    payload = {"email": "test@example.com", "course_slug": course.slug}
    response = csrf_enforcing_client.post(
        embed_enroll_url(embed_token),
        data=payload,
        content_type="application/json",
        HTTP_ORIGIN="https://third-party.example",
    )
    assert response.status_code == 200


def test_embed_enroll_view_rate_limits_by_ip_when_enabled(anonymous_client, course, embed_token, settings):
    cache.clear()
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
    }

    responses = []
    for i in range(21):
        payload = {"email": f"test{i}@example.com", "course_slug": course.slug}
        responses.append(
            anonymous_client.post(embed_enroll_url(embed_token), data=payload, content_type="application/json")
        )

    assert responses[-1].status_code == 429
    assert sum(1 for r in responses if r.status_code == 429) == 1


def test_embed_enroll_view_honours_configured_rate_limits(anonymous_client, course, embed_token, settings):
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
        payload = {"email": f"configured{i}@example.com", "course_slug": course.slug}
        responses.append(
            anonymous_client.post(embed_enroll_url(embed_token), data=payload, content_type="application/json")
        )

    assert [r.status_code for r in responses] == [200, 200, 429]


def test_embed_enroll_view_rate_limits_by_token_isolated_per_organization(
    anonymous_client, course, embed_token, settings
):
    cache.clear()
    course.enabled = True
    course.save()
    other_organization = Organization.objects.create(name="Other Org", embed_token=Organization.generate_embed_token())
    other_course = Course.objects.create(
        title="Other Course",
        slug="other-course",
        organization=other_organization,
        enabled=True,
        is_public=True,
    )
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "EMBEDDABLE_ENROLLMENT_ENABLED": True,
        "EMBEDDABLE_ENROLLMENT_RATE_LIMITS": {
            "PER_TOKEN_LIMIT": 1,
            "PER_TOKEN_WINDOW_SECONDS": 300,
        },
    }

    first = anonymous_client.post(
        embed_enroll_url(embed_token),
        data={"email": "a1@example.com", "course_slug": course.slug},
        content_type="application/json",
    )
    exhausted = anonymous_client.post(
        embed_enroll_url(embed_token),
        data={"email": "a2@example.com", "course_slug": course.slug},
        content_type="application/json",
    )
    assert first.status_code == 200
    assert exhausted.status_code == 429

    # A different organization's token has its own, unaffected bucket.
    other_response = anonymous_client.post(
        embed_enroll_url(other_organization.embed_token),
        data={"email": "b1@example.com", "course_slug": other_course.slug},
        content_type="application/json",
    )
    assert other_response.status_code == 200
