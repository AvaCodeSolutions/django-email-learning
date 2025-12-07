from django.urls import reverse
import pytest


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
    assert response.context["user_role"] == role


def test_context_values(superadmin_client):
    response = superadmin_client.get(get_url())
    assert response.status_code == 200
    assert "api_base_url" in response.context
    assert "platform_base_url" in response.context
    assert "active_organization_id" in response.context
    assert "user_role" in response.context
    assert response.context["page_title"] == "Courses"
    assert response.context["is_platform_admin"] is True
