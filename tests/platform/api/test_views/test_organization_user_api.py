from django.urls import reverse
import pytest


URL = reverse(
    "django_email_learning:api_platform:organization_users_view",
    kwargs={"organization_id": 1},
)


def test_create_organization_user_as_superadmin(superadmin_client, second_user):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "editor"


def test_admin_can_create_organization_user(platform_admin_client, second_user):
    response = platform_admin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "viewer"


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=["client"])
def test_other_roles_cannot_create_organization_user(client, second_user):
    response = client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 403


def test_anonymous_cannot_create_organization_user(anonymous_client, second_user):
    response = anonymous_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 401


def test_create_organization_user_with_invalid_role(superadmin_client, second_user):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "invalid_role",
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_create_organization_user_with_missing_fields(superadmin_client):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": 1,
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.json()


def create_organization_user_with_nonexistent_user(superadmin_client):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": 9999,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 409
    assert "error" in response.json()


def test_create_organization_user_in_nonexistent_organization(
    superadmin_client, second_user
):
    url = reverse(
        "django_email_learning:api_platform:organization_users_view",
        kwargs={"organization_id": 9999},
    )
    response = superadmin_client.post(
        url,
        data={
            "user_id": second_user.id,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 404
    assert "error" in response.json()
