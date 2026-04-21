from django_email_learning.services import jwt_service
from django_email_learning.personalised.api.views import QuizSubmissionView
from django_email_learning.personalised.api.serializers import QuestionResponse
from django.urls import reverse
import pytest

URL = reverse("django_email_learning:api_personalised:quiz_submission")


def test_quiz_submission_api_valid_token(content_delivery, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    response = anonymous_client.post(
        URL,
        data={
            "token": token,
            "answers": [
                {"id": q.id, "answers": []}
                for q in content_delivery.course_content.quiz.questions.all()
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["score"] == 0
    assert response.json()["passed"] is False
    assert (
        response.json()["required_score"]
        == content_delivery.course_content.quiz.required_score
    )

    # verify that the hash value has been updated
    content_delivery.refresh_from_db()
    assert content_delivery.hash_value != jwt_service.decode_jwt(token)["delivery_hash"]


def test_quiz_public_view_invalid_token(content_delivery, anonymous_client):
    response = anonymous_client.post(
        URL,
        data={
            "token": "Invalid",
            "answers": [
                {"id": q.id, "answers": []}
                for q in content_delivery.course_content.quiz.questions.all()
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "The signature is invalid" in response.json()["error"]


def test_calculate_score_and_passed_static_method(quiz_with_questions):
    answers = []
    for question in quiz_with_questions.questions.all():
        correct_answer_ids = list(
            question.answers.filter(is_correct=True).values_list("id", flat=True)
        )
        answers.append(QuestionResponse(id=question.id, answers=correct_answer_ids))

    score, passed = QuizSubmissionView.calculate_score_and_passed(
        quiz_with_questions, answers, question_ids=None
    )

    assert score == 100
    assert passed is True


@pytest.mark.parametrize(
    "quiz_is_blocking,expected_quiz_data_in_response",
    [
        (True, False),
        (False, True),
    ],
)
def test_quiz_data_is_returned_only_for_non_blocking_quiz(
    content_delivery, anonymous_client, quiz_is_blocking, expected_quiz_data_in_response
):
    quiz = content_delivery.course_content.quiz
    quiz.is_blocking = quiz_is_blocking
    quiz.save()

    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    response = anonymous_client.post(
        URL,
        data={
            "token": token,
            "answers": [
                {"id": q.id, "answers": []}
                for q in content_delivery.course_content.quiz.questions.all()
            ],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert (
        response.json()["quiz_data"] is not None
        if expected_quiz_data_in_response
        else response.json()["quiz_data"] is None
    )
