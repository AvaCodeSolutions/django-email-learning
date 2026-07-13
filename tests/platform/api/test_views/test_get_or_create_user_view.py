import pytest
from django.core import mail
from django.urls import reverse

from django_email_learning.models import Organization

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


def test_org_admin_cannot_act_on_behalf_of_another_organization(org_admin_client):
    Organization.objects.create(pk=2, name="Other Organization")

    # org_admin_client is an admin of organization 1, not organization 2 — the
    # decorator must check admin status against the organization_id in the
    # payload, not the requester's own active organization.
    response = org_admin_client.post(
        url,
        data={"email": "impersonated@example.com", "organization_id": 2},
        content_type="application/json",
    )

    assert response.status_code == 403
    assert len(mail.outbox) == 0


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
