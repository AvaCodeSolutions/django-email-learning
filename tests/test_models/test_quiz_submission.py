from django_email_learning.models import QuizSubmission, SentItem
from django.core.exceptions import ValidationError
import pytest


def test_quiz_submission_creation(db, course_quiz_content, enrollment):
    sent_item = SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    submission = QuizSubmission.objects.create(
        sent_item=sent_item,
        score=85,
        is_passed=False,
    )
    assert submission.id is not None
    assert submission.score == 85
    assert not submission.is_passed
    assert submission.submitted_at is not None


def test_quiz_submission_for_lesson_content(db, course_lesson_content, enrollment):
    sent_item = SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )

    with pytest.raises(Exception) as exc_info:
        QuizSubmission.objects.create(
            sent_item=sent_item,
            score=90,
            is_passed=True,
        )
    assert "Sent item must be associated with a quiz content." in str(exc_info.value)


@pytest.mark.parametrize(
    "score, is_passed",
    [
        (None, True),
        (50, None),
    ],
)
def test_sent_item_invalid_quiz_submission_fields(
    db, score, is_passed, course_quiz_content, enrollment
):
    sent_item = SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )

    with pytest.raises(ValidationError):
        QuizSubmission.objects.create(
            sent_item=sent_item,
            score=score,
            is_passed=is_passed,
        )
