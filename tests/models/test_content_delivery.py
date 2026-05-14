from django_email_learning.models import ContentDelivery
import pytest


def test_content_delivery_create(db, course_lesson_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    assert delivery.id is not None


def test_content_delivery_unique_constraint(db, course_lesson_content, enrollment):
    ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    with pytest.raises(Exception) as exc_info:
        ContentDelivery.objects.create(
            enrollment=enrollment,
            course_content=course_lesson_content,
        )
    assert (
        "content delivery with this enrollment and course content already exists"
        in str(exc_info.value).lower()
    )


def test_content_delivery_reminded_at_populated_for_quiz(
    db, course_quiz_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    assert delivery.remind_at is not None
    assert delivery.valid_until is not None


def test_content_delivery_reminded_at_not_populated_for_lesson(
    db, course_lesson_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    assert delivery.remind_at is None
    assert delivery.valid_until is None


def test_content_delivery_reminded_at_not_populated_for_quiz_with_no_deadline_and_no_reminder_interval(
    db, course_quiz_content, enrollment
):
    course_quiz_content.quiz.deadline_days = 0
    course_quiz_content.quiz.reminder_interval_days = 0
    course_quiz_content.save()
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    assert delivery.remind_at is None
    assert delivery.valid_until is None


def test_content_delivery_reminded_at_populated_for_quiz_with_no_deadline_and_reminder_interval(
    db, course_quiz_content, enrollment
):
    course_quiz_content.quiz.deadline_days = 0
    course_quiz_content.quiz.reminder_interval_days = 3
    course_quiz_content.save()
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    assert delivery.remind_at is not None
    assert delivery.valid_until is None
