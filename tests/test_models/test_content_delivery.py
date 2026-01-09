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
