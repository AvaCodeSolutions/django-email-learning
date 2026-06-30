import pytest
from django.urls import reverse


def get_url(course_id: int = 1) -> str:
    return reverse(
        "django_email_learning:platform:course_detail_view",
        kwargs={"course_id": course_id},
    )


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
def test_authenticated_user_access_course_detail_view(client, role, course):
    response = client.get(get_url(course.id))
    assert response.status_code == 200
    assert response.context["appContext"]["userRole"] == role


def test_context_values(superadmin_client, course):
    response = superadmin_client.get(get_url(course.id))
    assert response.status_code == 200
    assert "apiBaseUrl" in response.context["appContext"]
    assert "platformBaseUrl" in response.context["appContext"]
    assert "activeOrganizationId" in response.context
    assert "userRole" in response.context["appContext"]
    assert response.context["appContext"]["isPlatformAdmin"] is True
