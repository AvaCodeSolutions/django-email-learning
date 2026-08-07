"""Authentication and authorization for the v1 organization API.

Exercised through the courses endpoint, which is the cheapest authenticated
view; the decorator under test is shared by every endpoint in this API.
"""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import ApiKey, ApiKeyScope, ApiKeyType
from django_email_learning.services.jwt_service import generate_jwt

from .conftest import make_key

URL = reverse("django_email_learning:api_v1:courses")


def test_request_without_a_key_is_rejected(api_client, db):
    response = api_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


@pytest.mark.parametrize("header", ["Basic sometoken", "no-space", "Bearer a b"])
def test_malformed_authorization_header_is_rejected(api_client, db, header):
    response = api_client.get(URL, HTTP_AUTHORIZATION=header)
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid Authorization header format. Expected: Bearer <API_KEY>"}


def test_unknown_key_id_is_rejected(api_client, db):
    response = api_client.get(URL, HTTP_AUTHORIZATION="Bearer elk_deadbeef_notarealsecret")
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


def test_wrong_secret_for_a_real_key_id_is_rejected(api_client, db):
    api_key, _ = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Test key",
        organization_id=1,
        scopes=[ApiKeyScope.COURSES_READ],
    )
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer elk_{api_key.key_id}_wrongsecret")
    assert response.status_code == 401
    # Identical to the unknown-key-id message, so a caller can't confirm which
    # key ids exist by comparing responses.
    assert response.json() == {"error": "Invalid API key"}


def test_valid_key_is_accepted(api_client, db):
    token = make_key([ApiKeyScope.COURSES_READ])
    assert api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200


def test_platform_key_cannot_use_the_organization_api(api_client, db):
    """A platform key carries deployment-wide authority and no organization,
    so it must not fall through to an organization-scoped endpoint."""
    _, token = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 403


def test_organization_key_cannot_use_the_jobs_api(api_client, db):
    """The mirror image: an organization key must not reach platform endpoints."""
    token = make_key([ApiKeyScope.COURSES_READ])
    response = api_client.get(
        reverse("django_email_learning:api_jobs:check_imap_connections"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 403


def test_missing_scope_is_rejected(api_client, db):
    token = make_key([ApiKeyScope.ENROLLMENTS_WRITE])
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 403
    assert "courses:read" in response.json()["error"]


def test_revoked_key_is_rejected(api_client, db):
    api_key, token = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Test key",
        organization_id=1,
        scopes=[ApiKeyScope.COURSES_READ],
    )
    api_key.revoke()

    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 401
    assert response.json() == {"error": "API key has been revoked"}


def test_expired_key_is_rejected(api_client, db):
    _, token = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Test key",
        organization_id=1,
        scopes=[ApiKeyScope.COURSES_READ],
        expires_at=timezone.now() - datetime.timedelta(seconds=1),
    )
    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert response.status_code == 401
    assert response.json() == {"error": "API key has expired"}


def test_successful_request_records_last_used(api_client, db):
    api_key, token = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Test key",
        organization_id=1,
        scopes=[ApiKeyScope.COURSES_READ],
    )
    assert api_key.last_used_at is None

    api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    api_key.refresh_from_db()
    assert api_key.last_used_at is not None


def test_legacy_jwt_credentials_still_authenticate(api_client, db):
    """Keys issued before 3.1.0 were handed out as a JWT wrapping the raw key.
    The backfill hashed that same value, so the old token resolves through the
    new lookup and existing deployments don't break on upgrade.
    """
    api_key, token = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    _, secret = ApiKey.split_token(token)
    legacy_token = generate_jwt({"key": secret, "salt": "irrelevant"})

    response = api_client.get(
        reverse("django_email_learning:api_jobs:job_execution_status", kwargs={"job_execution_id": 1}),
        HTTP_AUTHORIZATION=f"Bearer {legacy_token}",
    )
    # 404 rather than 401: authentication succeeded, the job execution just
    # doesn't exist.
    assert response.status_code == 404
