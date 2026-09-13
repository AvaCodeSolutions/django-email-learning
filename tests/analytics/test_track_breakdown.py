from types import SimpleNamespace

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    CourseContent,
    DeactivationReason,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Lesson,
)

URL = reverse("django_email_learning:api_analytics:track_breakdown", kwargs={"organization_id": 1})


def make_content(course, priority, track=None, title=""):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title, content="..."),
        waiting_period=3600,
        is_published=True,
    )


@pytest.fixture
def branched_course(db, course):
    """Spine: Intro(1), Checkpoint(2), Wrap up(3).

    Remedial is one lesson that rejoins at Wrap up; Deep branches off Remedial and rejoins it.
    """
    intro = make_content(course, 1, title="Intro")
    checkpoint = make_content(course, 2, title="Checkpoint")
    wrap_up = make_content(course, 3, title="Wrap up")
    remedial = ContentTrack.objects.create(course=course, name="Remedial", merge_into=wrap_up)
    remedial_lesson = make_content(course, 1, remedial, title="Remedial lesson")
    deep = ContentTrack.objects.create(course=course, name="Deep", parent_track=remedial, merge_into=remedial_lesson)
    deep_lesson = make_content(course, 1, deep, title="Deep lesson")
    return SimpleNamespace(
        course=course,
        intro=intro,
        checkpoint=checkpoint,
        wrap_up=wrap_up,
        remedial_lesson=remedial_lesson,
        deep_lesson=deep_lesson,
    )


def enroll(course, email, route, status=EnrollmentStatus.ACTIVE):
    enrollment = Enrollment.objects.create(
        learner=Learner.objects.create(email=email, organization_id=1),
        course=course,
        status=EnrollmentStatus.ACTIVE,
    )
    for content in route:
        delivery = ContentDelivery.objects.create(enrollment=enrollment, course_content=content)
        DeliverySchedule.objects.create(delivery=delivery, status=DeliveryStatus.DELIVERED)
    if status != EnrollmentStatus.ACTIVE:
        enrollment.status = status
        if status == EnrollmentStatus.DEACTIVATED:
            enrollment.deactivation_reason = DeactivationReason.INACTIVE
        enrollment.save()
    return enrollment


def rows_for(client, course):
    response = client.get(f"{URL}?course_id={course.id}")
    assert response.status_code == 200
    return {row["name"]: row for row in response.json()["data"]}


def outcome(row):
    return (row["routed"], row["finished"], row["still_on_track"], row["left_course"])


def test_the_breakdown_needs_exactly_one_course(editor_client, branched_course):
    assert editor_client.get(URL).status_code == 400


def test_a_course_without_tracks_has_no_rows(editor_client, course):
    assert rows_for(editor_client, course) == {}


def test_learners_are_counted_by_how_they_left_each_track(editor_client, branched_course):
    b = branched_course
    enroll(b.course, "finished@example.com", [b.intro, b.checkpoint, b.remedial_lesson, b.wrap_up])
    enroll(b.course, "still@example.com", [b.intro, b.checkpoint, b.remedial_lesson])
    enroll(
        b.course,
        "left@example.com",
        [b.intro, b.checkpoint, b.remedial_lesson],
        status=EnrollmentStatus.DEACTIVATED,
    )
    enroll(b.course, "straight@example.com", [b.intro, b.checkpoint, b.wrap_up])

    rows = rows_for(editor_client, b.course)

    assert outcome(rows["Remedial"]) == (3, 1, 1, 1)
    assert outcome(rows["Deep"]) == (0, 0, 0, 0)


def test_branching_again_inside_a_track_is_still_being_on_it(editor_client, branched_course):
    b = branched_course
    enroll(b.course, "deep@example.com", [b.intro, b.checkpoint, b.remedial_lesson, b.deep_lesson])

    rows = rows_for(editor_client, b.course)

    assert outcome(rows["Remedial"]) == (1, 0, 1, 0)
    assert outcome(rows["Deep"]) == (1, 0, 1, 0)


def test_completing_the_course_from_a_track_counts_as_finishing_it(editor_client, branched_course):
    b = branched_course
    enroll(
        b.course,
        "done@example.com",
        [b.intro, b.checkpoint, b.remedial_lesson],
        status=EnrollmentStatus.COMPLETED,
    )

    assert outcome(rows_for(editor_client, b.course)["Remedial"]) == (1, 1, 0, 0)
