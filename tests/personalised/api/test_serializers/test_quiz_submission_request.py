from django_email_learning.personalised.api.serializers import QuizSubmissionRequest
import pytest


def test_quiz_submission_request_serializer_fields():
    data = {
        "token": "sample_token_123",
        "answers": [
            {"id": 1, "answers": {2, 3}},
            {"id": 2, "answers": {4}},
        ],
    }

    quiz_submission_request = QuizSubmissionRequest(**data)

    assert quiz_submission_request.token == data["token"]
    assert len(quiz_submission_request.answers) == 2
    assert quiz_submission_request.answers[0].id == 1
    assert quiz_submission_request.answers[0].answers == {2, 3}
    assert quiz_submission_request.answers[1].id == 2
    assert quiz_submission_request.answers[1].answers == {4}


def test_quiz_submission_request_serializer_duplicate_question_ids():
    data = {
        "token": "sample_token_123",
        "answers": [
            {"id": 1, "answers": {2, 3}},
            {"id": 1, "answers": {4}},  # Duplicate question ID
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        QuizSubmissionRequest(**data)

    assert "Duplicate question ID found: 1" in str(exc_info.value)
