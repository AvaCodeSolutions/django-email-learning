from django.urls import reverse
import pytest
from django.conf.global_settings import LANGUAGES


def get_url() -> str:
    return reverse("django_email_learning:platform:courses_view")


def test_anonymous_user_redirects_to_login(anonymous_client):
    response = anonymous_client.get(get_url())
    assert response.status_code == 302
    assert "/login/" in response.url


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
def test_authenticated_user_access_courses_view(client, role):
    response = client.get(get_url())
    assert response.status_code == 200
    assert response.context["appContext"]["userRole"] == role


def test_context_values(superadmin_client):
    response = superadmin_client.get(get_url())
    assert response.status_code == 200
    assert "apiBaseUrl" in response.context["appContext"]
    assert "platformBaseUrl" in response.context["appContext"]
    assert "activeOrganizationId" in response.context
    assert "userRole" in response.context["appContext"]
    assert response.context["appContext"]["languageOptions"] == [
        {"value": code, "label": name} for code, name in LANGUAGES
    ]
    assert response.context["page_title"] == "Courses"
    assert response.context["appContext"]["isPlatformAdmin"] is True
