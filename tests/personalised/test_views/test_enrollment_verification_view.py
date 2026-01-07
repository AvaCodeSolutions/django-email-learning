from django_email_learning.services import jwt_service
from django.urls import reverse
from unittest.mock import patch


URL = reverse("django_email_learning:personalised:verify_enrollment")


@patch("django_email_learning.personalised.views.VerifyEnrollmentCommand")
def test_verification_valid_token(command, enrollment, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "enrollment_id": enrollment.id,
            "verification_code": enrollment.activation_code,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}")

    assert command.return_value.execute.called
    assert response.status_code == 200
    assert "page_title" in response.context
    assert response.context["page_title"] == "Enrollment Verified"


def test_verification_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The verification link is not valid." in response.content.decode()


# # TODO: Add more tests for various scenarios
