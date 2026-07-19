import pytest
from django.urls import reverse

from django_email_learning.models import Course, Newsletter, Organization


def get_url(organization_id: int, course_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:course_embed_snippet",
        kwargs={"organization_id": organization_id, "course_id": course_id},
    )


def _make_public(course: Course) -> Course:
    course.enabled = True
    course.is_public = True
    course.save()
    return course


def test_embed_snippet_disabled_by_default(superadmin_client, course):
    _make_public(course)
    response = superadmin_client.get(get_url(1, course.id))
    assert response.status_code == 404


def test_embed_snippet_requires_public_and_enabled_course(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    # course fixture defaults to enabled=False
    response = superadmin_client.get(get_url(1, course.id))
    assert response.status_code == 409


def test_embed_snippet_not_found_for_unknown_course(superadmin_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = superadmin_client.get(get_url(1, 999999))
    assert response.status_code == 404


def test_embed_snippet_success(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    _make_public(course)

    response = superadmin_client.get(get_url(1, course.id))

    assert response.status_code == 200
    html = response.json()["html"]
    assert 'type="email"' in html
    assert course.slug in html
    assert "subscribe_to_newsletter" not in html or "<label" not in html


def test_embed_snippet_includes_newsletter_checkbox_when_linked(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    newsletter = Newsletter.objects.create(title="Weekly Digest", organization_id=1, language="en")
    course.newsletter = newsletter
    _make_public(course)

    response = superadmin_client.get(get_url(1, course.id))

    assert response.status_code == 200
    html = response.json()["html"]
    assert "<label" in html
    assert "Subscribe to Weekly Digest" in html


def test_embed_snippet_escapes_newsletter_title(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    newsletter = Newsletter.objects.create(title="News <script>alert(1)</script>", organization_id=1, language="en")
    course.newsletter = newsletter
    _make_public(course)

    response = superadmin_client.get(get_url(1, course.id))

    assert response.status_code == 200
    html = response.json()["html"]
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_embed_snippet_lazily_generates_token(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    _make_public(course)
    organization = Organization.objects.get(id=1)
    assert organization.embed_token is None

    response = superadmin_client.get(get_url(1, course.id))

    assert response.status_code == 200
    organization.refresh_from_db()
    assert organization.embed_token is not None
    assert organization.embed_token in response.json()["html"]


def test_embed_snippet_reuses_existing_token(superadmin_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    _make_public(course)

    first = superadmin_client.get(get_url(1, course.id))
    second = superadmin_client.get(get_url(1, course.id))

    organization = Organization.objects.get(id=1)
    assert organization.embed_token in first.json()["html"]
    assert organization.embed_token in second.json()["html"]


def test_embed_snippet_not_authenticated(anonymous_client, course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    _make_public(course)
    response = anonymous_client.get(get_url(1, course.id))
    assert response.status_code == 401


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 200), ("platform_admin", 200), ("viewer", 200), ("instructor", 200)],
    indirect=["client"],
)
def test_embed_snippet_user_access(client, course, settings, expected_status):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    _make_public(course)
    response = client.get(get_url(1, course.id))
    assert response.status_code == expected_status


@pytest.fixture()
def other_org_course(settings):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        description="Belongs to a different organization.",
        organization=other_org,
        enabled=True,
        is_public=True,
    )
    return course


def test_embed_snippet_cross_organization_returns_404(editor_client, other_org_course, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = editor_client.get(get_url(1, other_org_course.id))
    assert response.status_code == 404
