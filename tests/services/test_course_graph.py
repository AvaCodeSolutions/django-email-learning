"""A course's structure held in memory: what it answers, and that it answers in a fixed
number of queries however deeply the course's tracks nest.
"""

from types import SimpleNamespace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_email_learning.models import (
    ContentTrack,
    ContentTransition,
    CourseContent,
    Lesson,
    QuizOutcome,
    TransitionCondition,
)
from django_email_learning.services.content_sequence_service import next_content, remaining_after
from django_email_learning.services.course_graph import CourseGraph


def make_lesson(course, priority, track=None, published=True):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=f"Lesson {priority} on {track or 'spine'}", content="..."),
        waiting_period=60,
        is_published=published,
    )


def nested_course(course, quiz, depth):
    """Spine: Intro(1), Checkpoint quiz(2), Wrap up(3), and `depth` tracks nested in a chain.

    Failing the checkpoint routes onto the outermost track, which rejoins at Wrap up. Every
    track inside it holds one lesson and no merge point of its own, so a learner finishing
    the innermost one climbs the whole chain to find where to continue.
    """
    make_lesson(course, 1)
    checkpoint = CourseContent.objects.create(
        course=course, priority=2, type="quiz", quiz=quiz, waiting_period=60, is_published=True
    )
    wrap_up = make_lesson(course, 3)
    outermost = ContentTrack.objects.create(course=course, name="Level 0", merge_into=wrap_up)
    ContentTransition.objects.create(source=checkpoint, order=1, condition=TransitionCondition.FAILED, target=outermost)
    track = outermost
    entry = innermost = make_lesson(course, 1, track)
    for level in range(1, depth):
        track = ContentTrack.objects.create(course=course, name=f"Level {level}", parent_track=track)
        innermost = make_lesson(course, 1, track)
    return SimpleNamespace(
        checkpoint=checkpoint,
        wrap_up=wrap_up,
        outermost=outermost,
        entry=entry,
        innermost_track=track,
        innermost=innermost,
    )


DEPTHS = [1, ContentTrack.MAX_NESTING_DEPTH]


def test_a_nested_track_continues_at_the_nearest_merge_point_up_its_chain(db, course, quiz):
    shape = nested_course(course, quiz, depth=4)

    assert CourseGraph(course.id).continuation(shape.innermost_track) == shape.wrap_up


def test_a_track_being_edited_is_placed_against_the_course_as_stored(db, course, quiz):
    """clean() runs before save, so the unsaved parent is what the check must follow."""
    shape = nested_course(course, quiz, depth=3)
    shape.outermost.parent_track = shape.innermost_track

    assert CourseGraph(course.id).ancestors(shape.outermost)[0] == shape.innermost_track


@pytest.mark.parametrize("depth", DEPTHS)
def test_re_checking_a_course_costs_three_queries(db, course, quiz, depth, django_assert_num_queries):
    nested_course(course, quiz, depth)

    with django_assert_num_queries(3):
        course.validate_branching()


@pytest.mark.parametrize("depth", DEPTHS)
def test_leaving_the_innermost_track_costs_two_queries(db, course, quiz, depth, django_assert_num_queries):
    shape = nested_course(course, quiz, depth)

    with django_assert_num_queries(2):
        assert next_content(shape.innermost) == shape.wrap_up


def test_routing_onto_a_track_costs_three_queries(db, course, quiz, django_assert_num_queries):
    shape = nested_course(course, quiz, depth=3)

    with django_assert_num_queries(3):
        assert next_content(shape.checkpoint, outcome=QuizOutcome(score=10, passed=False)) == shape.entry


def test_a_step_on_a_course_that_does_not_branch_costs_one_query(db, course, django_assert_num_queries):
    first, second = make_lesson(course, 1), make_lesson(course, 2)

    with django_assert_num_queries(1):
        assert next_content(first) == second
    with django_assert_num_queries(1):
        assert next_content(second) is None


def test_checking_a_track_costs_the_same_however_deep_it_nests(db, course, quiz):
    shape = nested_course(course, quiz, depth=ContentTrack.MAX_NESTING_DEPTH - 1)

    def queries_to_check(parent):
        with CaptureQueriesContext(connection) as queries:
            ContentTrack(course=course, name=f"Under {parent.name}", parent_track=parent).full_clean()
        return len(queries)

    assert queries_to_check(shape.outermost) == queries_to_check(shape.innermost_track)


def test_a_graph_built_for_several_courses_counts_without_querying(db, course, quiz, django_assert_num_queries):
    shape = nested_course(course, quiz, depth=3)
    graph = CourseGraph.for_courses({course.id})[course.id]

    with django_assert_num_queries(0):
        assert remaining_after(graph, shape.innermost) == 1


def test_counting_what_remains_terminates_on_a_loop_of_published_merge_points(db, course):
    """`clean()` refuses this shape, so it is written with `.update()`, as a raw SQL fix would."""
    first_track = ContentTrack.objects.create(course=course, name="First")
    second_track = ContentTrack.objects.create(course=course, name="Second")
    on_first = make_lesson(course, 1, first_track)
    on_second = make_lesson(course, 1, second_track)
    ContentTrack.objects.filter(pk=first_track.pk).update(merge_into=on_second)
    ContentTrack.objects.filter(pk=second_track.pk).update(merge_into=on_first)

    assert remaining_after(CourseGraph(course.id), on_first) == 2
