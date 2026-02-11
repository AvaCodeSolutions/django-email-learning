from django_email_learning.services import jwt_service
from django.urls import reverse
from unittest.mock import patch


URL = reverse("django_email_learning:personalised:unsubscribe")


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_valid_token(command, enrollment, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "email": enrollment.learner.email,
            "course_slug": enrollment.course.slug,
            "organization_id": enrollment.course.organization.id,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}&confirm=true")

    assert command.return_value.execute.called
    assert response.status_code == 200
    assert "page_title" in response.context
    assert response.context["page_title"] == "Unsubscribed"
    assert (
        response.context["success_message"]
        == "You have been successfully unsubscribed from our mailing list."
    )


@patch("django_email_learning.personalised.views.UnsubscribeCommand")
def test_unsubscribe_valid_token_confirmation(command, enrollment, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "email": enrollment.learner.email,
            "course_slug": enrollment.course.slug,
            "organization_id": enrollment.course.organization.id,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}")

    assert not command.return_value.execute.called
    assert response.status_code == 200
    assert "page_title" in response.context
    assert response.context["page_title"] == "Confirm Unsubscription"
    assert (
        response.context["confirmation_message"]
        == "Are you sure you want to unsubscribe from our mailing list?"
    )
    assert "confirm_url" in response.context
    assert response.context["confirm_url"] == f"{URL}?token={token}&confirm=true"


def test_unsubscribe_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The link is not valid." in response.content.decode()
