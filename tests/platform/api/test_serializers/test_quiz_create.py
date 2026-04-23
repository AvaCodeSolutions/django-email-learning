from django_email_learning.platform.api.serializers import QuizCreate
import pytest


def test_quiz_create_serializer_fields():
    serializer = QuizCreate.model_validate(
        {
            "title": "Sample Quiz",
            "required_score": 80,
            "selection_strategy": "random",
            "deadline_days": 7,
            "questions": [
                {
                    "text": "What is 2 + 2?",
                    "priority": 1,
                    "answers": [
                        {"text": "3", "is_correct": False},
                        {"text": "4", "is_correct": True},
                        {"text": "5", "is_correct": False},
                    ],
                }
            ],
        }
    )
    assert serializer.title == "Sample Quiz"
    assert serializer.required_score == 80
    assert serializer.selection_strategy == "random"
    assert serializer.deadline_days == 7


def test_quiz_create_serializer_invalid_selection_strategy():
    with pytest.raises(ValueError) as excinfo:
        QuizCreate.model_validate(
            {
                "title": "Sample Quiz",
                "required_score": 80,
                "selection_strategy": "invalid_strategy",
                "deadline_days": 7,
                "questions": [
                    {
                        "text": "What is 2 + 2?",
                        "priority": 1,
                        "answers": [
                            {"text": "3", "is_correct": False},
                            {"text": "4", "is_correct": True},
                            {"text": "5", "is_correct": False},
                        ],
                    }
                ],
            }
        )
    assert "Input should be 'all' or 'random" in str(excinfo.value)


def test_quiz_create_serializer_deadline_days_bounds():
    with pytest.raises(ValueError) as excinfo_low:
        QuizCreate.model_validate(
            {
                "title": "Sample Quiz",
                "required_score": 80,
                "selection_strategy": "all",
                "deadline_days": -1,
                "questions": [
                    {
                        "text": "What is 2 + 2?",
                        "priority": 1,
                        "answers": [
                            {"text": "3", "is_correct": False},
                            {"text": "4", "is_correct": True},
                            {"text": "5", "is_correct": False},
                        ],
                    }
                ],
            }
        )
    assert "Input should be greater than or equal to 0" in str(excinfo_low.value)
