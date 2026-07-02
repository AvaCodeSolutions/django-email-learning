"""
Tests that isInstructor and isOrganizationAdmin in BasePlatformView.get_shared_context
are scoped to the active organization, not any organization.
"""

from django.test import Client
from django.urls import reverse


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


def test_navbar_custom_components_from_settings(db, users, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NAVBAR": {
            "CUSTOM_COMPONENTS": [
                {"SLOT": "notifications", "HTML": "<my-notifications></my-notifications>"},
                {"SLOT": "search", "HTML": "<my-search></my-search>"},
            ]
        },
    }
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["navbarCustomComponents"] == [
        {"slot": "notifications", "html": "<my-notifications></my-notifications>"},
        {"slot": "search", "html": "<my-search></my-search>"},
    ]
