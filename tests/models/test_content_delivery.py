from datetime import timedelta

import pytest
from django.utils import timezone

from django_email_learning.models import ContentDelivery


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
    assert "content delivery with this enrollment and course content already exists" in str(exc_info.value).lower()


def test_content_delivery_reminded_at_populated_for_quiz(db, course_quiz_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    assert delivery.remind_at is not None
    assert delivery.valid_until is not None


def test_content_delivery_reminded_at_not_populated_for_lesson(db, course_lesson_content, enrollment):
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


def test_record_reminder_sent_for_deadline_content_is_single_shot(db, course_quiz_content, enrollment):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PROCESSING,
    )

    delivery.record_reminder_sent()

    delivery.refresh_from_db()
    assert delivery.reminder_count == 1
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.SENT


def test_record_reminder_sent_re_arms_deadline_less_content_until_the_cap(db, course_quiz_content, enrollment):
    course_quiz_content.quiz.deadline_days = 0
    course_quiz_content.quiz.reminder_interval_days = 3
    course_quiz_content.quiz.save()
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PROCESSING,
    )

    # First two sends re-arm for another nudge ~3 days out.
    for expected_count in (1, 2):
        before = timezone.now()
        delivery.record_reminder_sent()
        delivery.refresh_from_db()
        assert delivery.reminder_count == expected_count
        assert delivery.reminder_state == ContentDelivery.ReminderStatus.PENDING
        assert delivery.remind_at >= before + timedelta(days=3) - timedelta(minutes=1)
        delivery.reminder_state = ContentDelivery.ReminderStatus.PROCESSING
        delivery.save()

    # Third send hits MAX_RECURRING_REMINDERS and stops.
    delivery.record_reminder_sent()
    delivery.refresh_from_db()
    assert delivery.reminder_count == 3
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
