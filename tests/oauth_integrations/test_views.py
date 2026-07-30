import json
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from django.urls import reverse

from django_email_learning.oauth_integrations.group_enrollment.base_group_enrollment_handler import (
    Group,
    User,
)
from django_email_learning.oauth_integrations.models import Session, SessionState
from django_email_learning.services import jwt_service

SESSIONS_URL = reverse("django_email_learning:oauth_integrations:sessions_view")
REDIRECT_URL = reverse("django_email_learning:oauth_integrations:redirect_view")


def oauth_group_list_url(session_id: str) -> str:
    return reverse(
        "django_email_learning:api_platform:oauth_sessions_groups",
        kwargs={"organization_id": 1, "session_id": session_id},
    )


def oauth_enroll_users_url(session_id: str) -> str:
    return reverse(
        "django_email_learning:api_platform:oauth_sessions_enroll",
        kwargs={"organization_id": 1, "session_id": session_id},
    )


def get_jwt(state: str = "test-state") -> str:
    return jwt_service.generate_jwt(
        {
            "provider_and_purpose": "google_group_enrollment",
            "course_id": 1,
            "state": state,
        }
    )


def session_detail_url(session_id: str) -> str:
    return reverse(
        "django_email_learning:api_platform:oauth_sessions_detail",
        kwargs={"organization_id": 1, "session_id": session_id},
    )


def oauth_payload(course_id: int) -> dict:
    return {
        "handler": {
            "provider_and_purpose": "google_group_enrollment",
            "course_id": course_id,
        }
    }


def test_create_session_unauthorized(anonymous_client, course):
    response = anonymous_client.post(
        SESSIONS_URL,
        json.dumps(oauth_payload(course.id)),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.parametrize("client", ["editor", "viewer", "instructor"], indirect=["client"])
def test_create_session_forbidden_for_editor(client, course):
    response = client.post(
        SESSIONS_URL,
        json.dumps(oauth_payload(course.id)),
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json() == {"error": "Forbidden"}


def test_create_session_returns_session_and_authorization_url(org_admin_client, course):
    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_authorization_url",
        return_value="https://accounts.google.com/o/oauth2/auth?state=abc",
    ):
        response = org_admin_client.post(
            SESSIONS_URL,
            json.dumps(oauth_payload(course.id)),
            content_type="application/json",
        )

    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    parsed_authorization_url = urlparse(data["authorization_url"])
    assert parsed_authorization_url.scheme == "https"
    assert parsed_authorization_url.hostname == "accounts.google.com"

    session = Session.objects.get(session_id=data["session_id"])
    assert session.jwt_token != "pending"


def test_create_session_access_denied_returns_403(org_admin_client, course):
    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler."
        "GoogleGroupEnrollmentHandler.access_allowed",
        return_value=False,
    ):
        response = org_admin_client.post(
            SESSIONS_URL,
            json.dumps(oauth_payload(course.id)),
            content_type="application/json",
        )

    assert response.status_code == 403
    assert response.json() == {"error": "Forbidden"}


def test_create_session_course_not_found(org_admin_client):
    response = org_admin_client.post(
        SESSIONS_URL,
        json.dumps(oauth_payload(999999)),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Course not found"}


def test_session_view_returns_session_state(db, org_admin_client):
    session_id = "test-session-id"
    session = Session.objects.create(
        session_id=session_id,
        state=SessionState.PROCESSING,
        jwt_token=get_jwt(state=session_id),
    )

    response = org_admin_client.get(session_detail_url(session.session_id))

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session.session_id,
        "state": SessionState.PROCESSING,
    }


def test_session_view_not_found(db, org_admin_client):
    response = org_admin_client.get(session_detail_url("missing-session"))

    assert response.status_code == 404
    assert response.json() == {"error": "Session not found"}


def test_redirect_missing_state_returns_html_error(anonymous_client):
    response = anonymous_client.get(REDIRECT_URL)

    assert response.status_code == 400
    assert "text/html" in response["Content-Type"]
    assert "Missing state parameter." in response.content.decode()


def test_redirect_missing_code_sets_failed_state(db, anonymous_client):
    session = Session.objects.create(jwt_token=get_jwt("test-state"))
    session.jwt_token = get_jwt(state=session.session_id)
    session.save()

    response = anonymous_client.get(f"{REDIRECT_URL}?state={session.session_id}")
    session.refresh_from_db()

    assert response.status_code == 400
    assert session.state == SessionState.FAILED
    assert "Missing code parameter." in response.content.decode()


def test_redirect_success_completes_session_and_executes_command(anonymous_client, course):
    session_id = "test-session-id"
    session = Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))
    decoded_request = {
        "provider_and_purpose": "google_group_enrollment",
        "course_id": course.id,
    }

    with (
        patch(
            "django_email_learning.oauth_integrations.views.decode_jwt",
            return_value=decoded_request,
        ),
        patch(
            "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.handle_redirect"
        ) as mocked_handle,
    ):
        mocked_handle.return_value = "test-access-token"
        response = anonymous_client.get(f"{REDIRECT_URL}?state={session.session_id}&code=test-code")

    session.refresh_from_db()
    assert response.status_code == 200
    assert session.state == SessionState.COMPLETED
    mocked_handle.assert_called_once()
    assert decoded_request["code"] == "test-code"
    assert decoded_request["state"] == session.session_id


def test_redirect_invalid_token_marks_failed(db, anonymous_client):
    session = Session.objects.create(jwt_token=get_jwt("test-state"))
    session.jwt_token = get_jwt(state=str(session.session_id))
    session.save()

    with patch(
        "django_email_learning.oauth_integrations.views.decode_jwt",
        side_effect=Exception("bad token"),
    ):
        response = anonymous_client.get(f"{REDIRECT_URL}?state={session.session_id}&code=test-code")

    session.refresh_from_db()
    assert response.status_code == 400
    assert session.state == SessionState.FAILED
    # Provider errors can carry tokens and client identifiers, so the page
    # shows a fixed message and the detail only goes to the log.
    content = response.content.decode()
    assert "bad token" not in content
    assert "Authorization failed" in content


# ---------------------------------------------------------------------------
# OauthGetGroupListView
# ---------------------------------------------------------------------------


def test_get_group_list_session_not_found(db, org_admin_client):
    response = org_admin_client.get(oauth_group_list_url("nonexistent-session"))

    assert response.status_code == 404
    assert response.json() == {"error": "Session not found"}


def test_get_group_list_returns_groups(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))
    groups = [
        Group(id="group-1", name="Engineering"),
        Group(id="group-2", name="Marketing"),
    ]

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_groups",
        return_value=groups,
    ):
        response = org_admin_client.get(oauth_group_list_url(session_id))

    assert response.status_code == 200
    assert response.json() == {
        "groups": [
            {"id": "group-1", "name": "Engineering"},
            {"id": "group-2", "name": "Marketing"},
        ]
    }


def test_get_group_list_returns_null_when_no_groups(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_groups",
        return_value=None,
    ):
        response = org_admin_client.get(oauth_group_list_url(session_id))

    assert response.status_code == 200
    assert response.json() == {"groups": None}


def test_get_group_list_returns_500_on_handler_error(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_groups",
        side_effect=Exception("Google API error"),
    ):
        response = org_admin_client.get(oauth_group_list_url(session_id))

    assert response.status_code == 500
    assert response.json() == {"error": "Failed to retrieve groups"}


# ---------------------------------------------------------------------------
# OauthGroupEnrollment
# ---------------------------------------------------------------------------


def test_enroll_users_unauthorized(db, anonymous_client):
    response = anonymous_client.post(
        oauth_enroll_users_url("any-session"),
        json.dumps({"groups": ["all"]}),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.parametrize("client", ["editor", "viewer", "instructor"], indirect=["client"])
def test_enroll_users_forbidden_for_editor(db, client):
    response = client.post(
        oauth_enroll_users_url("any-session"),
        json.dumps({"groups": ["all"]}),
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json() == {"error": "Forbidden"}


def test_enroll_users_session_not_found(db, org_admin_client):
    response = org_admin_client.post(
        oauth_enroll_users_url("nonexistent-session"),
        json.dumps({"groups": ["all"]}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Session not found"}


def test_enroll_users_invalid_payload(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))

    response = org_admin_client.post(
        oauth_enroll_users_url(session_id),
        json.dumps({"groups": []}),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_enroll_users_success(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))
    users_to_enroll = {User(email="alice@example.com"), User(email="bob@example.com")}

    with (
        patch(
            "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_users_to_enroll",
            return_value=users_to_enroll,
        ),
        patch("django_email_learning.platform.api.views.oauth.EnrollCommand") as mock_enroll,
        patch("django_email_learning.platform.api.views.oauth.VerifyEnrollmentCommand") as mock_verify,
    ):
        mock_enroll.return_value.execute.return_value = None
        mock_verify.return_value.execute.return_value = None
        response = org_admin_client.post(
            oauth_enroll_users_url(session_id),
            json.dumps({"groups": ["all"]}),
            content_type="application/json",
        )

    assert response.status_code == 200
    assert response.json() == {"message": "Enrollment process initiated"}


def test_enroll_users_returns_500_on_handler_error(db, org_admin_client, course):
    session_id = "test-session-id"
    Session.objects.create(session_id=session_id, jwt_token=get_jwt(state=session_id))

    with patch(
        "django_email_learning.oauth_integrations.group_enrollment.google_group_enrollment_handler.GoogleGroupEnrollmentHandler.get_users_to_enroll",
        side_effect=Exception("Directory API failure"),
    ):
        response = org_admin_client.post(
            oauth_enroll_users_url(session_id),
            json.dumps({"groups": ["all"]}),
            content_type="application/json",
        )

    assert response.status_code == 500
    assert response.json() == {"error": "Failed to enroll users"}
