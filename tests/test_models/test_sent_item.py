from django_email_learning.models import SentItem
import pytest


def test_sent_item_create(db, course_lesson_content, enrollment):
    sent_item = SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    assert sent_item.id is not None
    assert sent_item.send_events.count() == 1


def test_sent_item_unique_constraint(db, course_lesson_content, enrollment):
    SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    with pytest.raises(Exception) as exc_info:
        SentItem.objects.create(
            enrollment=enrollment,
            course_content=course_lesson_content,
        )
    assert (
        "sent item with this enrollment and course content already exists"
        in str(exc_info.value).lower()
    )
