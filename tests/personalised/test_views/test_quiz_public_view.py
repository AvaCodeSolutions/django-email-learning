from django_email_learning.services import jwt_service
from django.urls import reverse


URL = reverse("django_email_learning:personalised:quiz_public_view")


def test_quiz_public_view_valid_token(content_delivery, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}")
    assert response.status_code == 200
    assert "quiz" in response.context
    assert response.context["quiz"]["id"] == content_delivery.course_content.quiz.id


def test_quiz_public_view_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The link is not valid" in response.content.decode()


# TODO: Add more tests for various scenarios
