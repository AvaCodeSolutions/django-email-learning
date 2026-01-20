from django_email_learning.models import Organization
from django.test import override_settings
from django.core.files.storage import default_storage
from django.urls import reverse
import pytest


def get_url() -> str:
    return reverse("django_email_learning:api_platform:organizations_view")


def update_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:single_organization_view",
        kwargs={"organization_id": organization_id},
    )


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


@pytest.fixture
def existing_logo_path():
    with override_settings(
        STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}
    ):
        logo_path = "test_logo.png"
        with default_storage.open(logo_path, "w") as f:
            f.write("dummy image content")
        yield logo_path


def test_create_organization_for_existing_logo_file(
    superadmin_client, existing_logo_path
):
    # Create a dummy logo file in the default storage
    payload = {
        "name": "OrgName",
        "description": "Organization with existing logo file",
        "logo": existing_logo_path,
    }
    response = superadmin_client.post(
        get_url(), data=payload, content_type="application/json"
    )
    assert response.status_code == 201
    assert response.json().get("name") == "OrgName"
    assert response.json().get("logo").endswith(f"/{existing_logo_path}")


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


def test_update_organizations_view(superadmin_client, existing_logo_path):
    organization = Organization.objects.first()
    initial_name = organization.name
    initial_description = organization.description
    initial_logo = organization.logo
    payload = {
        "name": "Updated Org",
        "description": "Updated description",
        "logo": existing_logo_path,
    }
    response = superadmin_client.post(
        update_url(organization.id), data=payload, content_type="application/json"
    )
    assert response.status_code == 200

    assert response.json().get("name") == "Updated Org"
    assert response.json().get("description") == "Updated description"
    assert response.json().get("logo").endswith(f"/{existing_logo_path}")
    assert response.json().get("name") != initial_name
    assert response.json().get("description") != initial_description
    assert response.json().get("logo") != initial_logo


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=True)
def test_edit_organization_requires_platform_admin_or_superadmin(client):
    payload = {"name": "Updated Org", "description": "Updated description"}
    response = client.post(update_url(1), data=payload, content_type="application/json")
    assert response.status_code == 403
