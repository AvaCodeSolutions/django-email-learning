"""The v1 ping endpoint.

Authentication itself is covered in `test_authentication.py` against the shared
decorator; what matters here is that ping is authenticated at all, that it
needs no scope, and that it reports nothing beyond "the key is valid".
"""

from unittest import mock

from django.urls import reverse

from django_email_learning.models import ApiKey, ApiKeyType
from django_email_learning.organization_api.views import PingView

URL = reverse("django_email_learning:api_v1:ping")


def test_ping_returns_ok_for_a_valid_key(api_client, auth):
    response = api_client.get(URL, **auth)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping_requires_a_key(api_client, db):
    response = api_client.get(URL)

    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


def test_ping_enforces_no_scope():
    """A caller verifying its credential shouldn't have to hold a permission
    for an unrelated resource. Asserted against the decorator rather than by
    presenting a scopeless key, which the model doesn't allow to exist: this
    is what keeps holding true as new scopes are added.
    """
    assert PingView.get.required_api_key_scopes == frozenset()


def test_ping_rejects_a_platform_key(api_client, db):
    """This API is organization-scoped; a platform key must not authenticate
    against it, even for an endpoint that touches nothing."""
    _, token = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Platform key")

    response = api_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 403


def test_ping_leaks_nothing_about_the_organization(api_client, auth):
    """The body is a fixed literal. If it ever grows organization data it has
    to be a deliberate change, not something that arrives by accident."""
    assert api_client.get(URL, **auth).json() == {"status": "ok"}


def test_ping_is_rate_limited(api_client, auth):
    with mock.patch(
        "django_email_learning.organization_api.views.get_rate_limit_settings",
        return_value={"PER_KEY_LIMIT": 2, "PER_KEY_WINDOW_SECONDS": 60},
    ):
        assert api_client.get(URL, **auth).status_code == 200
        assert api_client.get(URL, **auth).status_code == 200
        response = api_client.get(URL, **auth)

    assert response.status_code == 429
    assert response.json()["error"] == "Too many requests. Please try again later."


def test_ping_rejects_other_methods(api_client, auth):
    """Only GET is routed; the decorator is attached to `get`, so anything else
    must be refused by Django rather than reaching an unauthenticated handler."""
    assert api_client.post(URL, **auth).status_code == 405
