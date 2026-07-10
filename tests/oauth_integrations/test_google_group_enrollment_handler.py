import base64
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler import (
    GoogleGroupEnrollmentHandler,
)
from django_email_learning.oauth_integrations.models import Session
from django_email_learning.services.jwt_service import generate_jwt
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE


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


def _mock_response(payload: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    return mock_resp


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


@pytest.fixture
def handler_with_session(db) -> GoogleGroupEnrollmentHandler:
    session_id = "test-state"
    Session.objects.create(
        session_id=session_id,
        jwt_token="",
        access_token=generate_jwt({"access_token": "fake-google-access-token"}),
    )
    return GoogleGroupEnrollmentHandler(course_id=1, state=session_id)


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


def test_get_user_saves_photo_to_private_storage(handler_with_session):
    photo_bytes = b"fake-photo-bytes"
    encoded_photo = base64.urlsafe_b64encode(photo_bytes).decode("ascii").rstrip("=")

    user_response = _mock_response({"primaryEmail": "learner@example.com"})
    photo_response = _mock_response({"photoData": encoded_photo, "mimeType": "image/jpeg"})

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.urlrequest.urlopen",
        side_effect=[user_response, photo_response],
    ):
        user = handler_with_session._get_user("google-user-id")

    assert user is not None
    assert user.email == "learner@example.com"
    assert user.photo_path is not None
    assert PRIVATE_FILE_STORAGE.exists(user.photo_path)
    assert PRIVATE_FILE_STORAGE.open(user.photo_path).read() == photo_bytes

    PRIVATE_FILE_STORAGE.delete(user.photo_path)


def test_get_user_without_email_returns_none(handler_with_session):
    user_response = _mock_response({})

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.urlrequest.urlopen",
        return_value=user_response,
    ):
        user = handler_with_session._get_user("google-user-id")

    assert user is None
