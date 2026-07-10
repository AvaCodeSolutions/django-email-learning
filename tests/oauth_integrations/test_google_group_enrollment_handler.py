import json
from unittest.mock import patch

import pytest
import requests

from django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler import (
    GoogleGroupEnrollmentHandler,
)


def _fake_token_response(scope: str) -> requests.Response:
    """
    Builds a requests.Response mimicking what Google's token endpoint
    returns, including a populated `.request` (oauthlib/requests_oauthlib
    logs `response.request.url`, so a bare Response() isn't enough).
    """
    payload = {
        "access_token": "fake-access-token",
        "expires_in": 3599,
        "scope": scope,
        "token_type": "Bearer",
        "id_token": "fake.id.token",
    }
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    response.request = requests.PreparedRequest()
    response.request.url = "https://oauth2.googleapis.com/token"
    response.request.headers = {}
    response.request.body = None
    return response


@pytest.fixture
def handler(settings) -> GoogleGroupEnrollmentHandler:
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "GOOGLE_OAUTH": {"CLIENT_ID": "fake-client-id", "CLIENT_SECRET": "fake-client-secret"},
        "SITE_BASE_URL": "http://localhost:8000",
    }
    h = GoogleGroupEnrollmentHandler(course_id=1, state="test-state", code="fake-code")
    h.code_verifier = "x" * 43
    return h


def test_handle_redirect_succeeds_when_google_grants_additional_scopes(handler, monkeypatch):
    """
    Google commonly grants scopes we didn't request (openid, userinfo.email,
    userinfo.profile) alongside the ones we did. oauthlib treats any scope
    mismatch as fatal unless OAUTHLIB_RELAX_TOKEN_SCOPE is set — without the
    fix, this raises `Warning: Scope has changed from ... to ...` and the
    OAuth redirect fails with a 400.
    """
    monkeypatch.delenv("OAUTHLIB_RELAX_TOKEN_SCOPE", raising=False)

    granted_scope = (
        "https://www.googleapis.com/auth/admin.directory.group.readonly "
        "https://www.googleapis.com/auth/userinfo.profile "
        "https://www.googleapis.com/auth/admin.directory.user.readonly "
        "https://www.googleapis.com/auth/userinfo.email openid"
    )

    with patch("requests.Session.send", return_value=_fake_token_response(granted_scope)):
        access_token = handler.handle_redirect()

    assert access_token == "fake-access-token"


def test_handle_redirect_succeeds_with_exact_scope_match(handler, monkeypatch):
    monkeypatch.delenv("OAUTHLIB_RELAX_TOKEN_SCOPE", raising=False)

    exact_scope = (
        "https://www.googleapis.com/auth/admin.directory.user.readonly "
        "https://www.googleapis.com/auth/admin.directory.group.readonly"
    )

    with patch("requests.Session.send", return_value=_fake_token_response(exact_scope)):
        access_token = handler.handle_redirect()

    assert access_token == "fake-access-token"
