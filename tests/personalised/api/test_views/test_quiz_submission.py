import datetime
from django.conf import settings
from django_email_learning.models import ContentDelivery
from django_email_learning.services import jwt_service
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.personalised.api.views import QuizSubmissionView
from django_email_learning.personalised.api.serializers import QuestionResponse
from django.urls import reverse
import pytest

URL = reverse("django_email_learning:api_personalised:quiz_submission")
AMP_URL = reverse("django_email_learning:api_personalised:quiz_amp_submission")
SOURCE_ORIGIN = email_sender_service.from_email
REQUEST_ORIGIN = settings.CSRF_TRUSTED_ORIGINS[0]


def test_quiz_submission_api_valid_token(content_delivery, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )
    original_remind_at = content_delivery.remind_at
    assert original_remind_at is not None

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
    assert content_delivery.remind_at != original_remind_at
    assert content_delivery.remind_at is not None
    assert content_delivery.hash_value != jwt_service.decode_jwt(token)["delivery_hash"]


def test_quiz_submission_when_quiz_is_passed(content_delivery, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    quiz = content_delivery.course_content.quiz
    answers = []
    for question in quiz.questions.all():
        correct_answer_ids = list(
            question.answers.filter(is_correct=True).values_list("id", flat=True)
        )
        answers.append(QuestionResponse(id=question.id, answers=correct_answer_ids))

    response = anonymous_client.post(
        URL,
        data={
            "token": token,
            "answers": [answer.model_dump(mode="json") for answer in answers],
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["score"] == 100
    assert response.json()["passed"] is True
    assert (
        response.json()["required_score"]
        == content_delivery.course_content.quiz.required_score
    )
    content_delivery.refresh_from_db()
    assert (
        content_delivery.reminder_state == ContentDelivery.ReminderStatus.NOT_APPLICABLE
    )
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


def test_amp_quiz_submission_invalid_token_returns_400_with_amp_headers(
    anonymous_client,
):
    response = anonymous_client.post(
        f"{AMP_URL}?__amp_source_origin={SOURCE_ORIGIN}",
        data={
            "token": "Invalid",
        },
        headers={
            "Origin": REQUEST_ORIGIN
        },  # Set origin to a trusted origin to bypass origin check
    )

    assert response.status_code == 400
    assert "The signature is invalid" in response.json()["error"]
    assert response["Access-Control-Allow-Origin"] == REQUEST_ORIGIN
    assert response["AMP-Access-Control-Allow-Source-Origin"] == SOURCE_ORIGIN
    assert response["Access-Control-Allow-Credentials"] == "true"


def test_amp_quiz_submission_expired_token_returns_410_with_amp_headers(
    content_delivery, anonymous_client
):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        },
        exp=datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    )

    response = anonymous_client.post(
        f"{AMP_URL}?__amp_source_origin={SOURCE_ORIGIN}",
        data={
            "token": token,
        },
        headers={
            "Origin": REQUEST_ORIGIN
        },  # Set origin to a trusted origin to bypass origin check
    )

    assert response.status_code == 410
    assert "The token is not valid anymore" in response.json()["error"]
    assert response["Access-Control-Allow-Origin"] == REQUEST_ORIGIN
    assert response["AMP-Access-Control-Allow-Source-Origin"] == SOURCE_ORIGIN
    assert response["Access-Control-Allow-Credentials"] == "true"


def test_amp_quiz_submission_success_returns_200_with_amp_headers(
    content_delivery, anonymous_client
):
    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )
    first_question = content_delivery.course_content.quiz.questions.first()
    assert first_question is not None

    response = anonymous_client.post(
        f"{AMP_URL}?__amp_source_origin={SOURCE_ORIGIN}",
        data={
            "token": token,
            str(first_question.id): "",
        },
        headers={
            "Origin": REQUEST_ORIGIN
        },  # Set origin to a trusted origin to bypass origin check
    )

    assert response.status_code == 200
    assert "score" in response.json()
    assert "passed" in response.json()
    assert response["Access-Control-Allow-Origin"] == REQUEST_ORIGIN
    assert response["AMP-Access-Control-Allow-Source-Origin"] == SOURCE_ORIGIN
    assert response["Access-Control-Allow-Credentials"] == "true"
