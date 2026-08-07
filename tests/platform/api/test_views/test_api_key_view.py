import json

import pytest
from django.urls import reverse

from django_email_learning.models import ApiKey, ApiKeyScope, ApiKeyType

URL = reverse("django_email_learning:api_platform:api_keys_list")


def _detail_url(api_key_id: int) -> str:
    return reverse("django_email_learning:api_platform:api_keys_detail", kwargs={"api_key_id": api_key_id})


def test_create_api_key_returns_the_token_once(superadmin_client):
    response = superadmin_client.post(URL)
    assert response.status_code == 201
    data = response.json()

    assert data["token"].startswith(f"elk_{data['key_id']}_")
    assert data["key_type"] == ApiKeyType.PLATFORM
    assert data["name"] == "Platform key"
    assert data["created_by"] == "superadmin"
    assert data["scopes"] == []
    assert data["organization_id"] is None


def test_listing_keys_never_returns_the_token(superadmin_client):
    create_response = superadmin_client.post(URL)
    token = create_response.json()["token"]

    response = superadmin_client.get(URL)
    assert response.status_code == 200
    api_keys = response.json()["api_keys"]

    assert len(api_keys) == 1
    assert api_keys[0]["key_id"] == create_response.json()["key_id"]
    # The whole point of hashing: nothing in the listing can be replayed.
    assert "token" not in api_keys[0]
    assert token not in json.dumps(api_keys)


def test_create_api_key_accepts_a_name(superadmin_client):
    response = superadmin_client.post(
        URL,
        data=json.dumps({"name": "CI runner"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    assert response.json()["name"] == "CI runner"


def test_listing_excludes_organization_keys(superadmin_client, db):
    ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Org key",
        organization_id=1,
        scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
    )
    superadmin_client.post(URL)

    api_keys = superadmin_client.get(URL).json()["api_keys"]
    assert [key["key_type"] for key in api_keys] == [ApiKeyType.PLATFORM]


def test_revoking_a_key_keeps_the_row(superadmin_client):
    api_key_id = superadmin_client.post(URL).json()["id"]

    response = superadmin_client.delete(_detail_url(api_key_id))
    assert response.status_code == 200
    assert response.json() == {"message": "API Key revoked successfully"}

    # Kept rather than deleted so the audit trail of what existed survives.
    api_key = ApiKey.objects.get(id=api_key_id)
    assert api_key.revoked_at is not None
    assert not api_key.is_usable


def test_revoking_an_unknown_key_returns_404(superadmin_client, db):
    assert superadmin_client.delete(_detail_url(9999)).status_code == 404


def test_platform_delete_cannot_reach_an_organization_key(superadmin_client, db):
    org_key, _ = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Org key",
        organization_id=1,
        scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
    )
    assert superadmin_client.delete(_detail_url(org_key.id)).status_code == 404


@pytest.mark.parametrize("client", ["editor", "viewer", "instructor"], indirect=["client"])
def test_organization_user_cannot_create_api_key(client):
    assert client.post(URL).status_code == 403


def test_platform_admin_can_create_api_key(platform_admin_client):
    assert platform_admin_client.post(URL).status_code == 201


def test_anonymous_cannot_create_api_key(anonymous_client, db):
    assert anonymous_client.post(URL).status_code == 401
