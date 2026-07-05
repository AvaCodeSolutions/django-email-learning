"""
Tests that isInstructor and isOrganizationAdmin in BasePlatformView.get_shared_context
are scoped to the active organization, not any organization.
"""

from django.test import Client
from django.urls import reverse

from django_email_learning.models import Organization, OrganizationUser
from django_email_learning.platform.views.base import BasePlatformView


def get_url() -> str:
    return reverse("django_email_learning:platform:courses_view")


def test_is_instructor_true_only_for_active_org(db, users):
    """isInstructor is True when the user is an instructor in the active org."""
    client = Client()
    client.force_login(users["instructor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isInstructor"] is True


def test_is_instructor_false_when_not_instructor_in_active_org(db, users):
    """isInstructor is False when the user is an editor (not instructor) in the active org."""
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isInstructor"] is False


def test_is_instructor_false_for_admin_without_display_name(db, users):
    """isInstructor is False for an admin org_user with no display_name (can_act_as_instructor requires one)."""
    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isInstructor"] is False


def test_is_instructor_true_for_admin_with_display_name(db, users):
    """isInstructor is True for a non-superuser admin org_user with a display_name, per can_act_as_instructor()."""
    admin_org_user = OrganizationUser.objects.get(user=users["organization_admin"], organization_id=1)
    admin_org_user.display_name = "Org Admin"
    admin_org_user.save()

    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isInstructor"] is True


def test_is_organization_admin_true_for_admin_in_active_org(db, users):
    """isOrganizationAdmin is True when the user is an admin in the active org."""
    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isOrganizationAdmin"] is True


def test_is_organization_admin_false_for_non_admin_in_active_org(db, users):
    """isOrganizationAdmin is False when the user is an editor in the active org."""
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["isOrganizationAdmin"] is False


def test_organization_is_public_true_by_default(db, users):
    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["organizationIsPublic"] is True


def test_organization_is_public_false_when_active_organization_not_public(db, users):
    Organization.objects.filter(id=1).update(is_public=False)

    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["organizationIsPublic"] is False


def test_newsletters_feature_absent_when_setting_falsy(db, users, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": None,
    }
    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert "newsletters" not in response.context["appContext"]["availableFeatures"]


def test_newsletters_feature_present_when_setting_enabled(db, users, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"FROM_EMAIL": "newsletter@example.com"},
    }
    client = Client()
    client.force_login(users["organization_admin"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert "newsletters" in response.context["appContext"]["availableFeatures"]


def test_navbar_custom_components_empty_by_default(db, users):
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["navbarCustomComponents"] == []
    assert response.context["navbarComponentStyleUrls"] == []
    assert response.context["navbarComponentScriptUrls"] == []


def _with_navbar_components(monkeypatch, components: list) -> None:
    original = BasePlatformView.get_shared_context

    def patched(self):  # type: ignore[no-untyped-def]
        context = original(self)
        context["appContext"]["navbarCustomComponents"] = components
        return context

    monkeypatch.setattr(BasePlatformView, "get_shared_context", patched)


def test_navbar_component_style_and_script_urls_deduped(db, users, monkeypatch):
    _with_navbar_components(
        monkeypatch,
        [
            {
                "slot": "a",
                "html": "<a-widget></a-widget>",
                "styleUrl": "/static/shared.css",
                "scriptUrl": "/static/shared.js",
            },
            {
                "slot": "b",
                "html": "<b-widget></b-widget>",
                "styleUrl": "/static/shared.css",
                "scriptUrl": "/static/other.js",
            },
        ],
    )
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["navbarComponentStyleUrls"] == ["/static/shared.css"]
    assert response.context["navbarComponentScriptUrls"] == ["/static/shared.js", "/static/other.js"]

    content = response.content.decode()
    assert content.count('href="/static/shared.css"') == 1
    assert '<script src="/static/shared.js"></script>' in content
    assert '<script src="/static/other.js"></script>' in content


def test_navbar_component_urls_omit_missing_style_or_script(db, users, monkeypatch):
    _with_navbar_components(
        monkeypatch,
        [{"slot": "a", "html": "<a-widget></a-widget>"}],
    )
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["navbarComponentStyleUrls"] == []
    assert response.context["navbarComponentScriptUrls"] == []
