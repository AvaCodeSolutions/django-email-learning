import pytest
from django.core.exceptions import ValidationError

from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    DeliveryStatus,
    QuizSubmission,
)


def test_quiz_submission_creation(db, course_quiz_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )

    DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=delivery)
    submission = QuizSubmission.objects.create(
        delivery=delivery,
        score=85,
        is_passed=False,
    )
    assert submission.id is not None
    assert submission.score == 85
    assert not submission.is_passed
    assert submission.submitted_at is not None


def test_quiz_submission_for_lesson_content(db, course_lesson_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    delivery.delivery_schedules.add(DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=delivery))
    with pytest.raises(Exception) as exc_info:
        QuizSubmission.objects.create(
            delivery=delivery,
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
def test_invalid_quiz_submission_fields(db, score, is_passed, course_quiz_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    delivery.delivery_schedules.add(DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=delivery))

    with pytest.raises(ValidationError):
        QuizSubmission.objects.create(
            delivery=delivery,
            score=score,
            is_passed=is_passed,
        )


def test_quiz_submission_check_sent_item_quiz_association(db, course_quiz_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )

    with pytest.raises(Exception) as exc_info:
        QuizSubmission.objects.create(
            delivery=delivery,
            score=75,
            is_passed=True,
        )
    assert "Quiz submission count exceeds the number of times the quiz was sent." in str(exc_info.value)
