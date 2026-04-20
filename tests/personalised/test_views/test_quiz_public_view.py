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
    assert "quiz" in response.context["appContext"]

    quiz = response.context["appContext"]["quiz"]
    assert quiz["id"] == content_delivery.course_content.quiz.id


def test_quiz_public_view_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The link is not valid" in response.content.decode()


def test_can_be_submited_multiple_times_if_not_passed_and_attempts_not_limited(
    content_delivery, anonymous_client
):
    quiz = content_delivery.course_content.quiz
    quiz.limited_attempts = False
    quiz.save()

    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    # First attempt - fail the quiz
    response = anonymous_client.post(
        reverse("django_email_learning:api_personalised:quiz_submission"),
        data={
            "token": token,
            "answers": [{"id": 1, "answers": []}],
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert not response.json()["passed"]

    # Second attempt - should be allowed since attempts are not limited and the quiz was not passed
    response = anonymous_client.get(f"{URL}?token={token}")
    assert response.status_code == 200


def test_cannot_be_submited_multiple_times_if_passed_and_attempts_not_limited(
    content_delivery, anonymous_client
):
    quiz = content_delivery.course_content.quiz
    quiz.limited_attempts = False
    quiz.required_score = 0  # Set required score to 0 to ensure passing
    quiz.save()

    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    # First attempt - pass the quiz
    response = anonymous_client.post(
        reverse("django_email_learning:api_personalised:quiz_submission"),
        data={
            "token": token,
            "answers": [{"id": 1, "answers": []}],
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["passed"]

    # Second attempt - should not be allowed since the quiz was passed
    response = anonymous_client.get(f"{URL}?token={token}")
    assert response.status_code == 410


# TODO: Add more tests for various scenarios
