from django_email_learning.personalised.api.serializers import QuestionResponse


def test_question_response_serializer_fields():
    data = {
        "id": 1,
        "answers": {2, 3, 4},
    }

    question_response = QuestionResponse(**data)

    assert question_response.id == data["id"]
    assert question_response.answers == data["answers"]


def test_question_response_serializer_duplicate_answer_ids():
    data = {
        "id": 1,
        "answers": [2, 2, 4, 2, 4],
    }

    question_response = QuestionResponse(**data)

    assert question_response.id == data["id"]
    assert question_response.answers == {2, 4}  # Duplicates in a set are ignored


def test_empty_answers_is_valid():
    data = {
        "id": 1,
        "answers": [],
    }

    question_response = QuestionResponse(**data)

    assert question_response.id == data["id"]
    assert question_response.answers == set()
