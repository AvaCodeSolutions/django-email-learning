import pytest
from django.core import mail
from django.urls import reverse

url = reverse("django_email_learning:api_platform:get_or_create_user_by_email")


@pytest.mark.parametrize("client", ["superadmin", "platform_admin"], indirect=["client"])
def test_get_or_create_user_view(client):
    response = client.post(
        url,
        data={"email": "testuser@example.com", "organization_id": 1},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["testuser@example.com"]


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=["client"])
def test_get_or_create_user_view_forbidden(client):
    response = client.post(
        url,
        data={"email": "testuser@example.com", "organization_id": 1},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_get_or_create_user_view_anonymous(anonymous_client):
    response = anonymous_client.post(
        url,
        data={"email": "testuser@example.com", "organization_id": 1},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_add_existing_user_to_organization(superadmin_client, users):
    response = superadmin_client.post(
        url,
        data={"email": users["editor_user"].email, "organization_id": 1},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == users["editor_user"].email

    # No new email should be sent when adding an existing user to the organization
    assert len(mail.outbox) == 0
