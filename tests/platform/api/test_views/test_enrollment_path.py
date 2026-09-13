from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DeliverySchedule,
    DeliveryStatus,
    Lesson,
    TransitionCondition,
)


def get_url(enrollment):
    return reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"enrollment_id": enrollment.id, "organization_id": 1},
    )


def make_lesson(course, priority, track=None, title=""):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title, content="..."),
        waiting_period=3600,
        is_published=True,
    )


def deliver(enrollment, content, status):
    delivery = ContentDelivery.objects.create(enrollment=enrollment, course_content=content)
    DeliverySchedule.objects.create(delivery=delivery, status=status)


def test_the_enrollment_reports_the_path_the_learner_took(viewer_client, course, active_enrollment, quiz):
    intro = make_lesson(course, 1, title="Intro")
    checkpoint = CourseContent.objects.create(
        course=course, priority=2, type="quiz", quiz=quiz, waiting_period=3600, is_published=True
    )
    wrap_up = make_lesson(course, 3, title="Wrap up")
    remedial = ContentTrack.objects.create(course=course, name="Remedial", merge_into=wrap_up)
    remedial_lesson = make_lesson(course, 1, remedial, title="Remedial lesson")
    ContentTransition.objects.create(source=checkpoint, order=1, condition=TransitionCondition.FAILED, target=remedial)
    deliver(active_enrollment, intro, DeliveryStatus.DELIVERED)
    deliver(active_enrollment, checkpoint, DeliveryStatus.DELIVERED)
    deliver(active_enrollment, remedial_lesson, DeliveryStatus.SCHEDULED)

    data = viewer_client.get(get_url(active_enrollment)).json()

    assert data["has_branching"] is True
    assert [(step["title"], step["track_name"], step["status"]) for step in data["path"]] == [
        ("Intro", None, "delivered"),
        ("Sample Quiz", None, "delivered"),
        ("Remedial lesson", "Remedial", "scheduled"),
    ]


def test_a_course_without_branching_says_so(viewer_client, content_delivery):
    data = viewer_client.get(get_url(content_delivery.enrollment)).json()

    assert data["has_branching"] is False
    assert [step["course_content_id"] for step in data["path"]] == [content_delivery.course_content_id]
