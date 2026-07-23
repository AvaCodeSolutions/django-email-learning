import pytest
from django.urls import reverse

from django_email_learning.models import Newsletter, Organization


def get_url(organization_id: int, newsletter_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:newsletter_embed_snippet",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter_id},
    )


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


def test_embed_snippet_disabled_by_default(superadmin_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": False}
    response = superadmin_client.get(get_url(1, newsletter.id))
    assert response.status_code == 404


def test_embed_snippet_not_found_for_unknown_newsletter(superadmin_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = superadmin_client.get(get_url(1, 999999))
    assert response.status_code == 404


def test_embed_snippet_success(superadmin_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = superadmin_client.get(get_url(1, newsletter.id))

    assert response.status_code == 200
    data = response.json()
    script_path = reverse("django_email_learning:public:embed_script")
    assert (
        data["script_html"] == f'<script src="{settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]}{script_path}"></script>'
    )
    assert "<del-newsletter-form" in data["widget_html"]
    assert f'newsletter_id="{newsletter.id}"' in data["widget_html"]


def test_embed_snippet_lazily_generates_token(superadmin_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    organization = Organization.objects.get(id=1)
    assert organization.embed_token is None

    response = superadmin_client.get(get_url(1, newsletter.id))

    assert response.status_code == 200
    organization.refresh_from_db()
    assert organization.embed_token is not None
    assert organization.embed_token in response.json()["widget_html"]


def test_embed_snippet_reuses_existing_token(superadmin_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    first = superadmin_client.get(get_url(1, newsletter.id))
    second = superadmin_client.get(get_url(1, newsletter.id))

    organization = Organization.objects.get(id=1)
    assert organization.embed_token in first.json()["widget_html"]
    assert organization.embed_token in second.json()["widget_html"]


def test_embed_snippet_not_authenticated(anonymous_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = anonymous_client.get(get_url(1, newsletter.id))
    assert response.status_code == 401


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 200), ("platform_admin", 200), ("viewer", 200), ("instructor", 200)],
    indirect=["client"],
)
def test_embed_snippet_user_access(client, newsletter, settings, expected_status):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = client.get(get_url(1, newsletter.id))
    assert response.status_code == expected_status


@pytest.fixture()
def other_org_newsletter(settings):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    return Newsletter.objects.create(title="Other Org Newsletter", language="en", organization=other_org)


def test_embed_snippet_cross_organization_returns_404(editor_client, other_org_newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}
    response = editor_client.get(get_url(1, other_org_newsletter.id))
    assert response.status_code == 404
