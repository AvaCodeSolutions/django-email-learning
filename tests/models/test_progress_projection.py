"""Platform progress over a branched learner's real path.

The total is what they have been sent plus what is still ahead, projected from where they
stand. Counting the whole course instead charges them for content their route skipped, so
a learner who finished would report 75%.
"""

import pytest

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    Lesson,
    TransitionCondition,
)


def content(course, priority, track=None, published=True, title=None):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title or f"p{priority}-{track}", content="..."),
        waiting_period=60,
        is_published=published,
    )


def deliver(enrollment, course_content, delivered=True):
    delivery = ContentDelivery.objects.create(enrollment=enrollment, course_content=course_content)
    DeliverySchedule.objects.create(
        delivery=delivery,
        status=DeliveryStatus.DELIVERED if delivered else DeliveryStatus.SCHEDULED,
    )
    return delivery


@pytest.fixture
def skipping_course(db, course, active_enrollment, course_quiz_content):
    """Spine 1,2,quiz(3),4,5,6 with a 2-item track at the quiz that rejoins at 6.

    Taking the track skips spine 4 and 5 - the whole point of a merge point that is not
    the very next content.
    """
    course_quiz_content.priority = 3
    course_quiz_content.is_published = True
    course_quiz_content.save()
    spine = {
        1: content(course, 1),
        2: content(course, 2),
        3: course_quiz_content,
        4: content(course, 4),
        5: content(course, 5),
        6: content(course, 6),
    }
    track = ContentTrack.objects.create(course=course, name="Shortcut", merge_into=spine[6])
    track_contents = [content(course, 1, track), content(course, 2, track)]
    ContentTransition.objects.create(
        source=course_quiz_content, order=1, condition=TransitionCondition.DEFAULT, target=track
    )
    return spine, track, track_contents


def test_finishing_a_skipping_path_reports_one_hundred(skipping_course, active_enrollment):
    spine, _, track_contents = skipping_course
    for item in [spine[1], spine[2], spine[3], *track_contents, spine[6]]:
        deliver(active_enrollment, item)

    assert active_enrollment.progress_percentage() == 100
    assert Enrollment.bulk_progress_percentages([active_enrollment])[active_enrollment.id] == 100


def test_finishing_a_terminal_track_reports_one_hundred(db, course, active_enrollment, skipping_course):
    """A track that ends the course skips everything after the branch point."""
    spine, _, _ = skipping_course
    terminal = ContentTrack.objects.create(course=course, name="Terminal")
    terminal_content = content(course, 1, terminal)
    ContentTransition.objects.create(source=spine[3], order=2, condition=TransitionCondition.PASSED, target=terminal)
    for item in [spine[1], spine[2], spine[3], terminal_content]:
        deliver(active_enrollment, item)

    assert active_enrollment.progress_percentage() == 100


def test_an_unbranched_learner_is_measured_against_the_spine(skipping_course, active_enrollment):
    spine, _, _ = skipping_course
    for item in [spine[1], spine[2], spine[3]]:
        deliver(active_enrollment, item)

    # Standing on the quiz, the projection falls through it: 4, 5 and 6 are still to come.
    assert active_enrollment.progress_percentage() == 50


def test_routing_onto_a_longer_path_lowers_the_percentage(db, course, active_enrollment, skipping_course):
    spine, _, _ = skipping_course
    long_track = ContentTrack.objects.create(course=course, name="Long", merge_into=spine[6])
    long_contents = [content(course, i, long_track) for i in range(1, 5)]
    ContentTransition.objects.create(source=spine[3], order=2, condition=TransitionCondition.PASSED, target=long_track)
    for item in [spine[1], spine[2], spine[3]]:
        deliver(active_enrollment, item)
    before = active_enrollment.progress_percentage()

    deliver(active_enrollment, long_contents[0], delivered=False)

    assert active_enrollment.progress_percentage() < before


def test_routing_onto_a_shortcut_raises_the_percentage(db, course, active_enrollment):
    """A learner sent past content they no longer need has less left, so the share rises."""
    spine = {i: content(course, i) for i in (1, 2, 3, 4, 5, 6, 7, 8)}
    short = ContentTrack.objects.create(course=course, name="Short", merge_into=spine[8])
    short_content = content(course, 1, short)
    ContentTransition.objects.create(source=spine[2], order=1, condition=TransitionCondition.DEFAULT, target=short)
    deliver(active_enrollment, spine[1])
    deliver(active_enrollment, spine[2])
    before = active_enrollment.progress_percentage()

    deliver(active_enrollment, short_content, delivered=False)

    assert active_enrollment.progress_percentage() > before


def test_bulk_and_single_agree_on_a_skipping_path(skipping_course, active_enrollment):
    spine, _, track_contents = skipping_course
    for item in [spine[1], spine[2], spine[3], track_contents[0]]:
        deliver(active_enrollment, item)

    assert (
        Enrollment.bulk_progress_percentages([active_enrollment])[active_enrollment.id]
        == active_enrollment.progress_percentage()
    )


def test_an_enrollment_with_no_deliveries_reports_zero(skipping_course, active_enrollment):
    assert active_enrollment.progress_percentage() == 0
    assert Enrollment.bulk_progress_percentages([active_enrollment])[active_enrollment.id] == 0
