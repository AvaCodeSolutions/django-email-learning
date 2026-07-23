import pytest
from django.conf.global_settings import LANGUAGES
from django.test import Client
from django.urls import reverse


def get_url() -> str:
    return reverse("django_email_learning:platform:root")


def test_anonymous_user_redirects_to_login(anonymous_client):
    response = anonymous_client.get(get_url())
    assert response.status_code == 302
    assert "/login/" in response.url


def test_fresh_login_with_no_session_organization_does_not_403(db, users):
    """
    Regression test: hitting the root Dashboard immediately after login (before any
    other page has seeded request.session["active_organization_id"]) must not 403.
    Dashboard has no URL-provided organization_id, so it must not be gated by a
    decorator that only reads the session rather than resolving it the same way
    get_or_set_active_organization does.
    """
    client = Client()
    client.force_login(users["editor_user"])

    response = client.get(get_url())

    assert response.status_code == 200


@pytest.mark.parametrize(
    "client,role",
    [
        ("superadmin", "admin"),
        ("platform_admin", "admin"),
        ("editor", "editor"),
        ("viewer", "viewer"),
    ],
    indirect=["client"],
)
def test_authenticated_user_access_dashboard(client, role):
    response = client.get(get_url())
    assert response.status_code == 200
    assert response.context["appContext"]["userRole"] == role


def test_context_values(superadmin_client):
    response = superadmin_client.get(get_url())
    assert response.status_code == 200
    assert "apiBaseUrl" in response.context["appContext"]
    assert "platformBaseUrl" in response.context["appContext"]
    assert "activeOrganizationId" in response.context
    assert response.context["appContext"]["languageOptions"] == [
        {"value": code, "label": name} for code, name in LANGUAGES
    ]
    assert response.context["page_title"] == "Dashboard"


def test_dashboard_setup_all_incomplete_for_brand_new_organization_state(org_admin_client, db):
    from django_email_learning.models import Course, OrganizationUser

    Course.objects.filter(organization_id=1).delete()
    OrganizationUser.objects.filter(organization_id=1).exclude(role="admin").delete()

    response = org_admin_client.get(get_url())

    assert response.status_code == 200
    setup = response.context["appContext"]["dashboardSetup"]
    assert setup["hasCourse"] is False
    assert setup["profileComplete"] is False


def test_dashboard_stats_present(org_admin_client):
    response = org_admin_client.get(get_url())

    assert response.status_code == 200
    stats = response.context["appContext"]["dashboardStats"]
    assert "activeCourses" in stats
    assert "enrolledLearners" in stats
    assert "newsletterSubscribers" in stats


def test_greeting_name_uses_org_user_display_name(instructor_client):
    response = instructor_client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["greetingName"] == "Instructor Name"


def test_greeting_name_is_none_without_display_name(editor_client):
    response = editor_client.get(get_url())

    assert response.status_code == 200
    assert response.context["appContext"]["greetingName"] is None
