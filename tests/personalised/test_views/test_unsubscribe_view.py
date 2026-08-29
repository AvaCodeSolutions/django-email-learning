from unittest.mock import patch

from django.urls import reverse

from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:personalised:unsubscribe")

# What a browser sends when a real person submits the confirm form: a
# same-origin top-level navigation. (Chrome/Firefox also add Sec-Fetch-User:
# ?1; Safari omits it, so it is not relied on.)
HUMAN_HEADERS = {
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
}


def _token(enrollment) -> str:
    return jwt_service.generate_jwt(
        {
            "email": enrollment.learner.email,
            "course_slug": enrollment.course.slug,
            "organization_id": enrollment.course.organization.id,
        }
    )


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_valid_token(command, enrollment, anonymous_client):
    # No Sec-Fetch-* headers (older client) -> the confirm checkbox is the gate.
    response = anonymous_client.post(URL, data={"token": _token(enrollment), "confirm": "on"})

    assert command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Unsubscribed"
    assert (
        response.context["appContext"]["successMessage"]
        == "You have been successfully unsubscribed from our mailing list."
    )


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_with_navigation_headers(command, enrollment, anonymous_client):
    response = anonymous_client.post(URL, data={"token": _token(enrollment), "confirm": "on"}, headers=HUMAN_HEADERS)

    assert command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Unsubscribed"


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_from_safari_without_sec_fetch_user_unsubscribes(command, enrollment, anonymous_client):
    # Safari sends Sec-Fetch-Site/Mode/Dest but not Sec-Fetch-User; a checked
    # box plus a same-origin navigation must still go through.
    response = anonymous_client.post(
        URL,
        data={"token": _token(enrollment), "confirm": "on"},
        headers={"Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"},
    )

    assert command.return_value.execute.called
    assert response.context["page_title"] == "Unsubscribed"


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_without_confirm_checkbox_does_not_unsubscribe(command, enrollment, anonymous_client):
    response = anonymous_client.post(URL, data={"token": _token(enrollment)}, headers=HUMAN_HEADERS)

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Confirm Unsubscription"
    assert response.context["appContext"]["localeMessages"]["confirm_required_message"]


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_via_fetch_call_does_not_unsubscribe(command, enrollment, anonymous_client):
    # A scripted fetch()/XHR POST rather than a form navigation.
    response = anonymous_client.post(
        URL,
        data={"token": _token(enrollment), "confirm": "on"},
        headers={"Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty"},
    )

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Confirm Unsubscription"


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_cross_site_post_does_not_unsubscribe(command, enrollment, anonymous_client):
    response = anonymous_client.post(
        URL,
        data={"token": _token(enrollment), "confirm": "on"},
        headers={**HUMAN_HEADERS, "Sec-Fetch-Site": "cross-site"},
    )

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Confirm Unsubscription"


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_valid_token_confirmation(command, enrollment, anonymous_client):
    token = _token(enrollment)

    response = anonymous_client.get(f"{URL}?token={token}")

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Confirm Unsubscription"
    assert (
        response.context["appContext"]["confirmationMessage"]
        == "Are you sure you want to unsubscribe from our mailing list?"
    )
    assert response.context["appContext"]["confirmUrl"] == URL
    assert response.context["appContext"]["confirmToken"] == token
    # The token must not leak into the confirm POST's Referer (and from there
    # into access logs / traces).
    assert response["Referrer-Policy"] == "strict-origin"


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_get_with_confirm_param_does_not_unsubscribe(command, enrollment, anonymous_client):
    response = anonymous_client.get(f"{URL}?token={_token(enrollment)}&confirm=true")

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert response.context["page_title"] == "Confirm Unsubscription"


def test_unsubscribe_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The link is not valid." in response.content.decode()
