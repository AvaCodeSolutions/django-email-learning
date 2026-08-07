import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from django_email_learning.models import (
    ApiKey,
    ApiKeyScope,
    ApiKeyType,
    Organization,
    OrganizationUser,
)


def _list_url(organization_id: int = 1) -> str:
    return reverse(
        "django_email_learning:api_platform:organization_api_keys_list",
        kwargs={"organization_id": organization_id},
    )


def _detail_url(api_key_id: int, organization_id: int = 1) -> str:
    return reverse(
        "django_email_learning:api_platform:organization_api_keys_detail",
        kwargs={"organization_id": organization_id, "api_key_id": api_key_id},
    )


def _create_payload(**overrides) -> dict:
    return {"name": "Partner integration", "scopes": [ApiKeyScope.ENROLLMENTS_WRITE.value], **overrides}


@pytest.fixture()
def other_organization(db) -> Organization:
    organization = Organization(name="Other Organization")
    organization.save()
    return organization


@pytest.fixture()
def other_org_admin_client(db, users, other_organization) -> Client:
    # Depends on `users` so the fixture's explicitly-numbered rows are inserted
    # before this one claims an auto id.
    user = User.objects.create(username="otherorgadmin", email="other@example.com")
    OrganizationUser.objects.create(user=user, organization=other_organization, role="admin")
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_organization_id"] = other_organization.id
    session.save()
    return client


def test_org_admin_can_create_a_scoped_key(org_admin_client):
    response = org_admin_client.post(
        _list_url(),
        data=json.dumps(_create_payload(scopes=[ApiKeyScope.ENROLLMENTS_WRITE.value, ApiKeyScope.COURSES_READ.value])),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()

    assert data["token"].startswith(f"elk_{data['key_id']}_")
    assert data["key_type"] == ApiKeyType.ORGANIZATION
    assert data["organization_id"] == 1
    assert data["scopes"] == [ApiKeyScope.COURSES_READ.value, ApiKeyScope.ENROLLMENTS_WRITE.value]
    assert data["created_by"] == "orgadmin"


def test_created_key_is_scoped_to_the_url_organization(org_admin_client):
    org_admin_client.post(_list_url(), data=json.dumps(_create_payload()), content_type="application/json")
    assert ApiKey.objects.get(key_type=ApiKeyType.ORGANIZATION).organization_id == 1


def test_listing_never_returns_the_token(org_admin_client):
    token = org_admin_client.post(
        _list_url(), data=json.dumps(_create_payload()), content_type="application/json"
    ).json()["token"]

    response = org_admin_client.get(_list_url())
    assert response.status_code == 200
    assert token not in json.dumps(response.json())


def test_listing_only_returns_this_organizations_keys(org_admin_client, other_organization):
    ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Someone else's key",
        organization_id=other_organization.id,
        scopes=[ApiKeyScope.COURSES_READ],
    )
    org_admin_client.post(_list_url(), data=json.dumps(_create_payload()), content_type="application/json")

    api_keys = org_admin_client.get(_list_url()).json()["api_keys"]
    assert [key["name"] for key in api_keys] == ["Partner integration"]


def test_listing_excludes_platform_keys(org_admin_client):
    ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    assert org_admin_client.get(_list_url()).json()["api_keys"] == []


def test_unknown_scope_is_rejected(org_admin_client):
    response = org_admin_client.post(
        _list_url(),
        data=json.dumps(_create_payload(scopes=["courses:destroy"])),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_scopes_are_required(org_admin_client):
    response = org_admin_client.post(
        _list_url(),
        data=json.dumps({"name": "No scopes"}),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_revoking_a_key(org_admin_client):
    api_key_id = org_admin_client.post(
        _list_url(), data=json.dumps(_create_payload()), content_type="application/json"
    ).json()["id"]

    response = org_admin_client.delete(_detail_url(api_key_id))
    assert response.status_code == 200
    assert ApiKey.objects.get(id=api_key_id).revoked_at is not None


def test_admin_cannot_revoke_another_organizations_key(other_org_admin_client, org_admin_client, other_organization):
    """The lookup filters on organization as well as id, so guessing a key id
    from another organization must not be enough to revoke it."""
    api_key_id = org_admin_client.post(
        _list_url(), data=json.dumps(_create_payload()), content_type="application/json"
    ).json()["id"]

    response = other_org_admin_client.delete(_detail_url(api_key_id, organization_id=other_organization.id))
    assert response.status_code == 404
    assert ApiKey.objects.get(id=api_key_id).revoked_at is None


def test_admin_cannot_create_a_key_for_another_organization(other_org_admin_client):
    response = other_org_admin_client.post(
        _list_url(organization_id=1),
        data=json.dumps(_create_payload()),
        content_type="application/json",
    )
    assert response.status_code == 403


def test_admin_cannot_list_another_organizations_keys(other_org_admin_client):
    assert other_org_admin_client.get(_list_url(organization_id=1)).status_code == 403


@pytest.mark.parametrize("client", ["editor", "viewer", "instructor"], indirect=["client"])
def test_non_admin_members_cannot_create_a_key(client):
    """A key acts with whatever scopes it carries, so issuing one would let a
    non-admin hand out access it doesn't itself have."""
    response = client.post(_list_url(), data=json.dumps(_create_payload()), content_type="application/json")
    assert response.status_code == 403


@pytest.mark.parametrize("client", ["editor", "viewer", "instructor"], indirect=["client"])
def test_non_admin_members_cannot_list_keys(client):
    assert client.get(_list_url()).status_code == 403


def test_anonymous_cannot_create_a_key(anonymous_client, db):
    response = anonymous_client.post(_list_url(), data=json.dumps(_create_payload()), content_type="application/json")
    assert response.status_code == 401
