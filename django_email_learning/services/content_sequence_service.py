"""Which content comes next in a course, and which one comes first.

A course is an ordered list: every `CourseContent` carries a `priority` unique
within its course, and a learner walks them in ascending order, skipping
anything unpublished. Both functions answer *which content* - creating the
delivery and its schedule is the caller's job.
"""

from typing import Optional

from django_email_learning.models.course_contents import CourseContent
from django_email_learning.models.courses import Course


def first_content(course: Course) -> Optional[CourseContent]:
    """The content a new enrollment starts on, or None if the course has none published."""
    return CourseContent.objects.filter(course=course, is_published=True).order_by("priority").first()


def next_content(current: CourseContent) -> Optional[CourseContent]:
    """The content that follows `current`, or None if it is the last published one.

    `current` itself does not have to be published: callers use this to step over
    content that was unpublished mid-course.
    """
    return (
        CourseContent.objects.filter(
            course_id=current.course_id,
            is_published=True,
            priority__gt=current.priority,
        )
        .order_by("priority")
        .first()
    )
