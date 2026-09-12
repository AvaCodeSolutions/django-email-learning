"""Which content comes next in a course, and which one comes first.

A course is an ordered list: every `CourseContent` carries a `priority` unique
within its course, and a learner walks them in ascending order, skipping
anything unpublished. That rule is small, but it was written out three separate
times - in `ContentDelivery.schedule_next_delivery`, in
`Enrollment.schedule_first_content_delivery` and in `CourseContent.get_next` -
and it is consulted from six places: the delivery job, the quiz submission
view, the assignment review path, the inactivity job, enrollment activation,
and the "up next" teaser in lesson emails.

Keeping one copy matters more than the duplication itself. Conditional routing
(sending a learner down one of several paths based on a quiz result) changes
what "next" means, and the change has to land in a single function rather than
being reapplied by hand to three queries that are free to drift apart.

Nothing here touches deliveries or schedules: these functions answer *which
content*, and the callers decide what to do with the answer.
"""

from typing import Optional

from django_email_learning.models.course_contents import CourseContent
from django_email_learning.models.courses import Course


def first_content(course: Course) -> Optional[CourseContent]:
    """The content a new enrollment starts on, or None if the course has none published."""
    return CourseContent.objects.filter(course=course, is_published=True).order_by("priority").first()


def next_content(current: CourseContent) -> Optional[CourseContent]:
    """The content that follows `current`, or None if it is the last published one.

    `current` itself does not have to be published - the delivery job calls this
    to step over content that was unpublished mid-course.
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
