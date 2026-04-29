from django.urls import reverse
import pytest

URL = reverse("django_email_learning:api_platform:api_key_view")


def test_create_api_key(superadmin_client):
    response = superadmin_client.post(URL)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "key" in data
    assert "created_at" in data
    assert data["created_by"] == "superadmin"
    created_key = data["key"]

    response = superadmin_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "api_keys" in data
    api_keys = data["api_keys"]
    assert any(api_key["key"] == created_key for api_key in api_keys)


@pytest.mark.parametrize(
    "client", ["editor", "viewer", "instructor"], indirect=["client"]
)
def test_organization_user_cannot_create_api_key(client):
    response = client.post(URL)
    assert response.status_code == 403


def test_platform_admin_can_create_api_key(platform_admin_client):
    response = platform_admin_client.post(URL)
    assert response.status_code == 201
