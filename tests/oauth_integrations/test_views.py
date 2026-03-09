import json
from unittest.mock import patch

from django.urls import reverse

from django_email_learning.oauth_integrations.models import Session, SessionState


SESSIONS_URL = reverse("django_email_learning:oauth_integrations:sessions_view")
REDIRECT_URL = reverse("django_email_learning:oauth_integrations:redirect_view")


def session_detail_url(session_id: str) -> str:
    return reverse(
        "django_email_learning:oauth_integrations:session_view",
        kwargs={"session_id": session_id},
    )


def oauth_payload(course_id: int) -> dict:
    return {
        "request": {
            "command": {
                "command_name": "enroll_from_google_directory",
                "course_id": course_id,
            }
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


def test_create_session_forbidden_for_editor(editor_client, course):
    response = editor_client.post(
        SESSIONS_URL,
        json.dumps(oauth_payload(course.id)),
        content_type="application/json",
    )

    assert response.status_code == 403
    assert response.json() == {"error": "Forbidden"}


def test_create_session_returns_session_and_authorization_url(org_admin_client, course):
    with patch(
        "django_email_learning.services.command_models.enroll_from_google_directory_command.EnrollFromGoogleDirectoryCommand.get_authorization_url",
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
    assert data["authorization_url"].startswith("https://accounts.google.com")

    session = Session.objects.get(session_id=data["session_id"])
    assert session.jwt_token != "pending"


def test_create_session_course_not_found(org_admin_client):
    response = org_admin_client.post(
        SESSIONS_URL,
        json.dumps(oauth_payload(999999)),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Course not found"}


def test_session_view_returns_session_state(db, anonymous_client):
    session = Session.objects.create(jwt_token="token", state=SessionState.PROCESSING)

    response = anonymous_client.get(session_detail_url(session.session_id))

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session.session_id,
        "state": SessionState.PROCESSING,
    }


def test_session_view_not_found(db, anonymous_client):
    response = anonymous_client.get(session_detail_url("missing-session"))

    assert response.status_code == 404
    assert response.json() == {"error": "Session not found"}


def test_redirect_missing_state_returns_html_error(anonymous_client):
    response = anonymous_client.get(REDIRECT_URL)

    assert response.status_code == 400
    assert "text/html" in response["Content-Type"]
    assert "Missing state parameter." in response.content.decode()


def test_redirect_missing_code_sets_failed_state(db, anonymous_client):
    session = Session.objects.create(jwt_token="token")

    response = anonymous_client.get(f"{REDIRECT_URL}?state={session.session_id}")
    session.refresh_from_db()

    assert response.status_code == 400
    assert session.state == SessionState.FAILED
    assert "Missing code parameter." in response.content.decode()


def test_redirect_success_completes_session_and_executes_command(
    anonymous_client, course
):
    session = Session.objects.create(jwt_token="token")
    decoded_request = {
        "command": {
            "command_name": "enroll_from_google_directory",
            "course_id": course.id,
        }
    }

    with patch(
        "django_email_learning.oauth_integrations.views.decode_jwt",
        return_value=decoded_request,
    ), patch(
        "django_email_learning.oauth_integrations.views.CommandHandlerService.handle_json_command"
    ) as mocked_handle:
        response = anonymous_client.get(
            f"{REDIRECT_URL}?state={session.session_id}&code=test-code"
        )

    session.refresh_from_db()
    assert response.status_code == 200
    assert session.state == SessionState.COMPLETED
    assert mocked_handle.called

    handled_payload = mocked_handle.call_args.args[0]
    assert handled_payload["command"]["code"] == "test-code"
    assert handled_payload["command"]["state"] == session.session_id


def test_redirect_invalid_token_marks_failed(db, anonymous_client):
    session = Session.objects.create(jwt_token="token")

    with patch(
        "django_email_learning.oauth_integrations.views.decode_jwt",
        side_effect=Exception("bad token"),
    ):
        response = anonymous_client.get(
            f"{REDIRECT_URL}?state={session.session_id}&code=test-code"
        )

    session.refresh_from_db()
    assert response.status_code == 400
    assert session.state == SessionState.FAILED
    assert "bad token" in response.content.decode()
