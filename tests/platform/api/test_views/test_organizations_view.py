import pytest
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner, Organization, SocialLink


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
        "social_links": [
            {"platform": "website", "url": "https://new-org.example.com"},
            {"platform": "linkedin", "url": "https://www.linkedin.com/company/new-org"},
            {"platform": "youtube", "url": "https://www.youtube.com/@new-org"},
        ],
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 201
    assert response.json().get("name") == "New Org"
    assert sorted(response.json().get("social_links"), key=lambda link: link["platform"]) == sorted(
        payload["social_links"], key=lambda link: link["platform"]
    )


def test_post_organizations_view_rejects_invalid_social_link_platform(superadmin_client):
    payload = {
        "name": "Invalid Platform Org",
        "description": "Should be rejected",
        "social_links": [{"platform": "myspace", "url": "https://myspace.com/new-org"}],
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 400


def test_create_organization_strips_html_from_description(superadmin_client):
    payload = {
        "name": "Scripted Org",
        "description": "Nice org<script>alert(document.cookie)</script>",
    }
    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")
    assert response.status_code == 201
    assert "<script>" not in response.json()["description"]


def test_update_organization_strips_html_from_description(superadmin_client):
    payload = {"description": 'Hijacked description <img src=x onerror="alert(1)">'}
    response = superadmin_client.post(update_url(1), data=payload, content_type="application/json")
    assert response.status_code == 200
    assert "onerror" not in response.json()["description"]
    assert "Hijacked description" in Organization.objects.get(id=1).description


def test_post_organizations_view_optional_social_fields(superadmin_client):
    payload = {"name": "Optional Org", "description": "Optional fields omitted"}

    response = superadmin_client.post(get_url(), data=payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json().get("social_links") == []

    organization = Organization.objects.get(id=response.json()["id"])
    assert organization.social_links.count() == 0


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
    initial_social_links = list(organization.social_links.values("platform", "url"))
    payload = {
        "name": "Updated Org",
        "description": "Updated description",
        "logo": existing_logo_path,
        "social_links": [
            {"platform": "website", "url": "https://updated-org.example.com"},
            {"platform": "linkedin", "url": "https://www.linkedin.com/company/updated-org"},
            {"platform": "youtube", "url": "https://www.youtube.com/@updated-org"},
        ],
    }
    response = superadmin_client.post(update_url(organization.id), data=payload, content_type="application/json")
    assert response.status_code == 200

    assert response.json().get("name") == "Updated Org"
    assert response.json().get("description") == "Updated description"
    assert response.json().get("logo").endswith(f"/{existing_logo_path}")
    assert sorted(response.json().get("social_links"), key=lambda link: link["platform"]) == sorted(
        payload["social_links"], key=lambda link: link["platform"]
    )
    assert response.json().get("name") != initial_name
    assert response.json().get("description") != initial_description
    assert response.json().get("logo") != initial_logo
    assert response.json().get("social_links") != initial_social_links


def test_update_organizations_view_optional_social_fields(superadmin_client):
    organization = Organization.objects.first()
    SocialLink.objects.create(organization=organization, platform="website", url="https://existing-org.example.com")
    SocialLink.objects.create(
        organization=organization, platform="linkedin", url="https://www.linkedin.com/company/existing-org"
    )
    SocialLink.objects.create(
        organization=organization, platform="youtube", url="https://www.youtube.com/@existing-org"
    )

    payload = {
        "name": "Renamed Org",
        "description": "Updated without changing social links",
    }

    response = superadmin_client.post(update_url(organization.id), data=payload, content_type="application/json")

    assert response.status_code == 200
    expected_social_links = sorted(
        [{"platform": link.platform, "url": link.url} for link in organization.social_links.all()],
        key=lambda link: link["platform"],
    )
    assert sorted(response.json().get("social_links"), key=lambda link: link["platform"]) == expected_social_links

    organization.refresh_from_db()
    assert organization.social_links.count() == 3


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
