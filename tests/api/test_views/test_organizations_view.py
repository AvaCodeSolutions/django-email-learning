from django_email_learning.models import Organization
from django.urls import reverse
import pytest


def get_url() -> str:
    return reverse("django_email_learning:api:organizations_view")


@pytest.fixture(autouse=True)
def second_organization(db):
    org = Organization(name="Second Org", description="The second organization")
    org.save()
    return org


def test_get_organizations_view_as_superadmin(superadmin_client):
    response = superadmin_client.get(get_url())
    assert response.status_code == 200
    assert len(response.json().get("organizations")) == 2


@pytest.mark.parametrize(
    "client", ["viewer", "editor", "platform_admin"], indirect=True
)
def test_get_organizations_view_as_organization_user(client):
    response = client.get(get_url())
    assert response.status_code == 200
    assert len(response.json().get("organizations")) == 1
    assert response.json().get("organizations")[0].get("name") != "Second Org"


def test_get_organizations_view_as_anonymous(anonymous_client):
    response = anonymous_client.get(get_url())
    assert response.status_code == 401


def test_post_organizations_view_as_superadmin(superadmin_client):
    payload = {"name": "New Org", "description": "A newly created organization"}
    response = superadmin_client.post(
        get_url(), data=payload, content_type="application/json"
    )
    assert response.status_code == 201
    assert response.json().get("name") == "New Org"


@pytest.mark.parametrize(
    "client", ["viewer", "editor", "platform_admin"], indirect=True
)
def test_post_organizations_view_as_organization_user(client):
    payload = {"name": "Another Org", "description": "Should not be created"}
    response = client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 403


def test_post_organizations_view_as_anonymous(anonymous_client):
    payload = {"name": "Anonymous Org", "description": "Should not be created"}
    response = anonymous_client.post(
        get_url(), data=payload, content_type="application/json"
    )
    assert response.status_code == 401
