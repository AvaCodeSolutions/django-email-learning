import pytest
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner, Organization


def get_url() -> str:
    return reverse("django_email_learning:api_platform:organizations_list")


def update_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:organizations_detail",
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


@pytest.mark.parametrize("client", ["viewer", "editor", "platform_admin"], indirect=True)
def test_get_organizations_view_as_organization_user(client):
    response = client.get(get_url())
    assert response.status_code == 200
    assert len(response.json().get("organizations")) == 1
    assert response.json().get("organizations")[0].get("name") != "Second Org"


def test_get_organizations_view_as_anonymous(anonymous_client):
    response = anonymous_client.get(get_url())
    assert response.status_code == 401


def test_post_organizations_view_as_superadmin(superadmin_client):
    payload = {
        "name": "New Org",
        "description": "A newly created organization",
        "website": "https://new-org.example.com",
        "linkedin_page": "https://www.linkedin.com/company/new-org",
        "youtube_channel": "https://www.youtube.com/@new-org",
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 201
    assert response.json().get("name") == "New Org"
    assert response.json().get("website") == payload["website"]
    assert response.json().get("linkedin_page") == payload["linkedin_page"]
    assert response.json().get("youtube_channel") == payload["youtube_channel"]


def test_post_organizations_view_optional_social_fields(superadmin_client):
    payload = {"name": "Optional Org", "description": "Optional fields omitted"}

    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json().get("website") is None
    assert response.json().get("linkedin_page") is None
    assert response.json().get("youtube_channel") is None

    organization = Organization.objects.get(id=response.json()["id"])
    assert organization.website is None
    assert organization.linkedin_page is None
    assert organization.youtube_channel is None


@pytest.fixture
def existing_logo_path():
    with override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}):
        logo_path = "test_logo.png"
        with default_storage.open(logo_path, "w") as f:
            f.write("dummy image content")
        yield logo_path


def test_create_organization_for_existing_logo_file(superadmin_client, existing_logo_path):
    # Create a dummy logo file in the default storage
    payload = {
        "name": "OrgName",
        "description": "Organization with existing logo file",
        "logo": existing_logo_path,
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 201
    assert response.json().get("name") == "OrgName"
    assert response.json().get("logo").endswith(f"/{existing_logo_path}")


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=True)
def test_post_organizations_view_as_organization_user(client):
    payload = {"name": "Another Org", "description": "Should not be created"}
    response = client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 403


def test_post_organizations_view_as_anonymous(anonymous_client):
    payload = {"name": "Anonymous Org", "description": "Should not be created"}
    response = anonymous_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 401


def test_update_organizations_view(superadmin_client, existing_logo_path):
    organization = Organization.objects.first()
    initial_name = organization.name
    initial_description = organization.description
    initial_logo = organization.logo
    initial_website = organization.website
    initial_linkedin_page = organization.linkedin_page
    initial_youtube_channel = organization.youtube_channel
    payload = {
        "name": "Updated Org",
        "description": "Updated description",
        "logo": existing_logo_path,
        "website": "https://updated-org.example.com",
        "linkedin_page": "https://www.linkedin.com/company/updated-org",
        "youtube_channel": "https://www.youtube.com/@updated-org",
    }
    response = superadmin_client.post(update_url(organization.id), data=payload, content_type="application/json")
    assert response.status_code == 200

    assert response.json().get("name") == "Updated Org"
    assert response.json().get("description") == "Updated description"
    assert response.json().get("logo").endswith(f"/{existing_logo_path}")
    assert response.json().get("website") == payload["website"]
    assert response.json().get("linkedin_page") == payload["linkedin_page"]
    assert response.json().get("youtube_channel") == payload["youtube_channel"]
    assert response.json().get("name") != initial_name
    assert response.json().get("description") != initial_description
    assert response.json().get("logo") != initial_logo
    assert response.json().get("website") != initial_website
    assert response.json().get("linkedin_page") != initial_linkedin_page
    assert response.json().get("youtube_channel") != initial_youtube_channel


def test_update_organizations_view_optional_social_fields(superadmin_client):
    organization = Organization.objects.first()
    organization.website = "https://existing-org.example.com"
    organization.linkedin_page = "https://www.linkedin.com/company/existing-org"
    organization.youtube_channel = "https://www.youtube.com/@existing-org"
    organization.save()

    payload = {
        "name": "Renamed Org",
        "description": "Updated without changing social links",
    }

    response = superadmin_client.post(update_url(organization.id), data=payload, content_type="application/json")

    assert response.status_code == 200
    assert response.json().get("website") == organization.website
    assert response.json().get("linkedin_page") == organization.linkedin_page
    assert response.json().get("youtube_channel") == organization.youtube_channel

    organization.refresh_from_db()
    assert organization.website == "https://existing-org.example.com"
    assert organization.linkedin_page == "https://www.linkedin.com/company/existing-org"
    assert organization.youtube_channel == "https://www.youtube.com/@existing-org"


@pytest.mark.parametrize("client", ["viewer", "editor", "instructor"], indirect=True)
def test_edit_organization_forbidden_for_non_admin_roles(client):
    payload = {"name": "Updated Org", "description": "Updated description"}
    response = client.post(update_url(1), data=payload, content_type="application/json")
    assert response.status_code == 403


def test_edit_organization_allowed_for_org_admin(org_admin_client):
    payload = {"name": "Org Admin Updated", "description": "Updated by org admin"}
    response = org_admin_client.post(update_url(1), data=payload, content_type="application/json")
    assert response.status_code == 200
    assert response.json().get("name") == "Org Admin Updated"


def test_edit_organization_forbidden_for_org_admin_of_different_org(org_admin_client, second_organization):
    payload = {"name": "Should Fail", "description": "Wrong org"}
    response = org_admin_client.post(
        update_url(second_organization.id),
        data=payload,
        content_type="application/json",
    )
    assert response.status_code == 403


def test_delete_organization(superadmin_client):
    organization = Organization.objects.first()
    response = superadmin_client.delete(update_url(organization.id))
    assert response.status_code == 200
    assert not Organization.objects.filter(id=organization.id).exists()


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=True)
def test_delete_organization_requires_platform_admin_or_superadmin(client):
    organization = Organization.objects.first()
    response = client.delete(update_url(organization.id))
    assert response.status_code == 403


def test_create_private_organization(superadmin_client):
    payload = {
        "name": "Private Org",
        "description": "This organization is private",
        "is_public": False,
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 201
    assert response.json().get("is_public") is False


def test_update_organization_to_private(superadmin_client):
    organization = Organization.objects.first()
    assert organization.is_public is True
    payload = {
        "name": organization.name,
        "description": organization.description,
        "is_public": False,
    }
    response = superadmin_client.post(update_url(organization.id), data=payload, content_type="application/json")
    assert response.status_code == 200
    assert response.json().get("is_public") is False

    organization.refresh_from_db()
    assert organization.is_public is False


def test_can_enroll_learner_reflects_cap(org_admin_client, settings, course):
    organization = Organization.objects.get(id=1)

    response = org_admin_client.get(update_url(organization.id))
    assert response.status_code == 200
    assert response.json().get("can_enroll_learner") is True

    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    learner = Learner.objects.create(email="learner@example.com", organization=organization)
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)

    response = org_admin_client.get(update_url(organization.id))
    assert response.status_code == 200
    assert response.json().get("can_enroll_learner") is False
