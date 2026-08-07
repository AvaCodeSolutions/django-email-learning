from unittest import mock

from django.urls import reverse

URL = reverse("django_email_learning:api_v1:courses")


def test_listing_courses(api_client, auth, enabled_course):
    response = api_client.get(URL, **auth)
    assert response.status_code == 200

    courses = response.json()["courses"]
    assert len(courses) == 1
    assert courses[0]["slug"] == enabled_course.slug
    assert courses[0]["title"] == enabled_course.title
    assert courses[0]["enabled"] is True


def test_listing_excludes_other_organizations_courses(api_client, auth, enabled_course, other_organization_course):
    courses = api_client.get(URL, **auth).json()["courses"]
    assert [c["slug"] for c in courses] == [enabled_course.slug]


def test_listing_includes_disabled_courses(api_client, auth, course):
    """A caller needs to see a disabled course to understand why enrolling into
    it fails, so the listing isn't filtered by `enabled`."""
    courses = api_client.get(URL, **auth).json()["courses"]
    assert [c["enabled"] for c in courses] == [False]


def test_rate_limit_returns_429(api_client, auth, enabled_course):
    with mock.patch(
        "django_email_learning.organization_api.views.get_rate_limit_settings",
        return_value={"PER_KEY_LIMIT": 2, "PER_KEY_WINDOW_SECONDS": 60},
    ):
        assert api_client.get(URL, **auth).status_code == 200
        assert api_client.get(URL, **auth).status_code == 200
        response = api_client.get(URL, **auth)

    assert response.status_code == 429
    assert response.json()["error"] == "Too many requests. Please try again later."


def test_rate_limit_is_per_key(api_client, auth, enabled_course, db):
    """Budgets are keyed on key_id, so one caller exhausting its allowance
    can't lock out another key on the same organization."""
    from django_email_learning.models import ApiKeyScope

    from .conftest import make_key

    other_token = make_key([ApiKeyScope.COURSES_READ])

    with mock.patch(
        "django_email_learning.organization_api.views.get_rate_limit_settings",
        return_value={"PER_KEY_LIMIT": 1, "PER_KEY_WINDOW_SECONDS": 60},
    ):
        assert api_client.get(URL, **auth).status_code == 200
        assert api_client.get(URL, **auth).status_code == 429
        assert api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {other_token}").status_code == 200
