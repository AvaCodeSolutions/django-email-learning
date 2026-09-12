"""Submitting a quiz that carries routing rules.

A branch point answers with a route rather than a verdict: the first submission sends the
learner wherever their result points, so the retry, the attempt limit and the two-strikes
deactivation never come into play. Everything here is about that difference - the
unbranched behaviour is covered in test_quiz_submission.py and is untouched.
"""

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    TransitionCondition,
)
from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:api_personalised:quiz_submission")


@pytest.fixture
def remedial_track(db, course, content_delivery):
    """A remedial track the quiz routes failures onto, plus spine content to rejoin at."""
    quiz_content = content_delivery.course_content
    wrap_up = CourseContent.objects.create(
        course=course,
        priority=quiz_content.priority + 1,
        type="lesson",
        lesson=Lesson.objects.create(title="Wrap up", content="..."),
        waiting_period=60,
        is_published=True,
    )
    track = ContentTrack.objects.create(course=course, name="Remedial", merge_into=wrap_up)
    remedial_content = CourseContent.objects.create(
        course=course,
        track=track,
        priority=1,
        type="lesson",
        lesson=Lesson.objects.create(title="Remedial lesson", content="..."),
        waiting_period=60,
        is_published=True,
    )
    return track, remedial_content, wrap_up


def submit(client, delivery, answers=None):
    token = jwt_service.generate_jwt({"delivery_id": delivery.id, "delivery_hash": delivery.hash_value})
    return client.post(
        URL,
        data={
            "token": token,
            "answers": answers
            if answers is not None
            else [{"id": q.id, "answers": []} for q in delivery.course_content.quiz.questions.all()],
        },
        content_type="application/json",
    )


def test_failing_a_branch_point_routes_instead_of_retrying(content_delivery, anonymous_client, remedial_track):
    """Without rules this same submission would schedule a retry a day later."""
    _, remedial_content, _ = remedial_track
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.FAILED,
        target=remedial_track[0],
    )

    response = submit(anonymous_client, content_delivery)

    assert response.status_code == 200
    assert response.json()["passed"] is False
    scheduled = ContentDelivery.objects.filter(enrollment=content_delivery.enrollment).exclude(id=content_delivery.id)
    assert [delivery.course_content for delivery in scheduled] == [remedial_content]


def test_failing_a_branch_point_schedules_no_retry(content_delivery, anonymous_client, remedial_track):
    """Without rules, failing a limited-attempts quiz re-sends it a day later.

    That retry is the first step of the two-strikes rule, which exists because a failure
    otherwise has nowhere to go. A branch point does have somewhere, so neither happens:
    the learner is routed and the enrollment stays active.
    """
    content_delivery.course_content.quiz.limited_attempts = True
    content_delivery.course_content.quiz.save()
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.FAILED,
        target=remedial_track[0],
    )
    schedules_before = content_delivery.delivery_schedules.count()

    submit(anonymous_client, content_delivery)

    content_delivery.refresh_from_db()
    assert content_delivery.delivery_schedules.count() == schedules_before
    content_delivery.enrollment.refresh_from_db()
    assert content_delivery.enrollment.status == EnrollmentStatus.ACTIVE


def test_a_branch_point_retires_its_link_on_the_first_submission(content_delivery, anonymous_client, remedial_track):
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.DEFAULT,
        target=remedial_track[0],
    )
    original_hash = content_delivery.hash_value

    response = submit(anonymous_client, content_delivery)

    assert response.json()["is_invalidated"] is True
    content_delivery.refresh_from_db()
    assert content_delivery.hash_value != original_hash
    assert content_delivery.valid_until is None
    assert content_delivery.reminder_state == ContentDelivery.ReminderStatus.NOT_APPLICABLE


def test_a_practice_quiz_branch_point_routes_on_the_first_submission(
    content_delivery, anonymous_client, remedial_track
):
    """A non-blocking quiz branches on the same rule as a blocking one."""
    _, remedial_content, _ = remedial_track
    content_delivery.course_content.quiz.is_blocking = False
    content_delivery.course_content.quiz.save()
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.DEFAULT,
        target=remedial_track[0],
    )

    submit(anonymous_client, content_delivery)

    scheduled = ContentDelivery.objects.filter(enrollment=content_delivery.enrollment).exclude(id=content_delivery.id)
    assert [delivery.course_content for delivery in scheduled] == [remedial_content]


def test_routing_onto_a_terminal_track_graduates_the_learner(content_delivery, anonymous_client, course):
    terminal = ContentTrack.objects.create(course=course, name="Terminal")
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.DEFAULT,
        target=terminal,
    )

    submit(anonymous_client, content_delivery)

    content_delivery.enrollment.refresh_from_db()
    assert content_delivery.enrollment.status == EnrollmentStatus.COMPLETED


def test_a_branched_learner_reports_no_progress(content_delivery, anonymous_client, remedial_track):
    _, remedial_content, _ = remedial_track
    ContentTransition.objects.create(
        source=content_delivery.course_content,
        order=1,
        condition=TransitionCondition.DEFAULT,
        target=remedial_track[0],
    )
    enrollment = content_delivery.enrollment
    assert enrollment.progress_percentage() is not None

    submit(anonymous_client, content_delivery)

    assert enrollment.has_branched() is True
    assert enrollment.progress_percentage() is None
    assert Enrollment.bulk_progress_percentages([enrollment])[enrollment.id] is None


def test_an_unbranched_learner_still_reports_progress(content_delivery, course):
    enrollment = content_delivery.enrollment
    content_delivery.delivery_schedules.update(status=DeliveryStatus.DELIVERED)

    assert enrollment.progress_percentage() is not None
    assert Enrollment.bulk_progress_percentages([enrollment])[enrollment.id] is not None
