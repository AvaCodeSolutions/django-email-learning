from django_email_learning.models import SentItem, Enrollment, CourseContent
import pytest


@pytest.fixture
def course_content(db, course, lesson) -> CourseContent:
    content = CourseContent.objects.create(
        course=course, priority=1, type="lesson", lesson=lesson, waiting_period=10
    )
    return content


@pytest.fixture
def enrollment(db, learner, course) -> Enrollment:
    enrollment = Enrollment.objects.create(learner=learner, course=course)
    return enrollment


def test_sent_item_create(db, course_content, enrollment):
    sent_item = SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_content,
    )
    assert sent_item.id is not None
    assert sent_item.send_events.count() == 1


def test_sent_item_unique_constraint(db, course_content, enrollment):
    SentItem.objects.create(
        enrollment=enrollment,
        course_content=course_content,
    )
    with pytest.raises(Exception) as exc_info:
        SentItem.objects.create(
            enrollment=enrollment,
            course_content=course_content,
        )
    assert (
        "sent item with this enrollment and course content already exists"
        in str(exc_info.value).lower()
    )
