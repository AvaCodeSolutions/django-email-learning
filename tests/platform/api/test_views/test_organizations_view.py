from django_email_learning.models import Organization
from django.test import override_settings
from django.core.files.storage import default_storage
from django.urls import reverse
import pytest


def get_url() -> str:
    return reverse("django_email_learning:api_platform:organizations_view")


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


def test_create_organization_ignore_none_exisiting_logo_file(superadmin_client):
    payload = {
        "name": "Org with Logo",
        "description": "Organization with non-existing logo file",
        "logo": "non_existing_logo.png",
    }
    response = superadmin_client.post(
        get_url(), data=payload, content_type="application/json"
    )
    assert response.status_code == 201
    assert response.json().get("name") == "Org with Logo"
    assert response.json().get("logo") is None


@override_settings(
    STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}
)
def test_create_organization_for_existing_logo_file(superadmin_client):
    # Create a dummy logo file in the default storage
    logo_path = "existing_logo.png"
    with default_storage.open(logo_path, "w") as f:
        f.write("dummy image content")

    payload = {
        "name": "OrgName",
        "description": "Organization with existing logo file",
        "logo": logo_path,
    }
    response = superadmin_client.post(
        get_url(), data=payload, content_type="application/json"
    )
    assert response.status_code == 201
    assert response.json().get("name") == "OrgName"
    assert response.json().get("logo").endswith(f"/{logo_path}")


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
