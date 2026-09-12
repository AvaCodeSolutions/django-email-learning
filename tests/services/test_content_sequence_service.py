import pytest

from django_email_learning.models import Course, CourseContent, Lesson
from django_email_learning.services.content_sequence_service import first_content, next_content


@pytest.fixture
def lessons(db, course):
    """Four lesson contents at priorities 1-4, all published."""
    contents = []
    for priority in range(1, 5):
        lesson = Lesson.objects.create(title=f"Lesson {priority}", content="...")
        contents.append(
            CourseContent.objects.create(
                course=course,
                priority=priority,
                type="lesson",
                lesson=lesson,
                waiting_period=3600,
                is_published=True,
            )
        )
    return contents


def test_first_content_is_the_lowest_published_priority(lessons):
    assert first_content(lessons[0].course) == lessons[0]


def test_first_content_skips_unpublished_content(lessons):
    lessons[0].is_published = False
    lessons[0].save()

    assert first_content(lessons[0].course) == lessons[1]


def test_first_content_is_none_when_nothing_is_published(lessons):
    CourseContent.objects.update(is_published=False)

    assert first_content(lessons[0].course) is None


def test_first_content_ignores_other_courses(db, course, lessons, imap_connection):
    """Two courses' contents share a priority space, so the course filter is load-bearing."""
    other_course = Course.objects.create(
        title="Other Course",
        slug="other-course",
        imap_connection=imap_connection,
        organization_id=1,
    )
    other_lesson = Lesson.objects.create(title="Other Lesson", content="...")
    CourseContent.objects.create(
        course=other_course,
        priority=1,
        type="lesson",
        lesson=other_lesson,
        waiting_period=3600,
        is_published=True,
    )

    assert first_content(course) == lessons[0]


def test_next_content_follows_priority_order(lessons):
    assert next_content(lessons[0]) == lessons[1]
    assert next_content(lessons[1]) == lessons[2]


def test_next_content_skips_unpublished_content(lessons):
    lessons[1].is_published = False
    lessons[1].save()

    assert next_content(lessons[0]) == lessons[2]


def test_next_content_is_none_after_the_last_published_content(lessons):
    assert next_content(lessons[3]) is None


def test_next_content_steps_off_unpublished_content(lessons):
    """The delivery job calls this on content that was unpublished mid-course."""
    lessons[1].is_published = False
    lessons[1].save()

    assert next_content(lessons[1]) == lessons[2]


def test_next_content_ignores_non_contiguous_priorities(lessons):
    """Priorities are an ordering, not a counter: gaps must not stop the walk."""
    last = lessons[3]
    last.priority = 97
    last.save()

    assert next_content(lessons[2]) == last
