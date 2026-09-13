import pytest

from django_email_learning.models import (
    ContentTrack,
    ContentTransition,
    Course,
    CourseContent,
    Lesson,
    QuizOutcome,
    TransitionCondition,
)
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


@pytest.fixture
def branch(db, course, lessons):
    """A track branching off the spine, merging back into the last spine content.

    Spine:  1, 2, 3, 4  (the `lessons` fixture)
    Track:  A, B        merging into spine content 4
    """
    track = ContentTrack.objects.create(course=course, name="Remedial path", merge_into=lessons[3])
    contents = []
    for priority, title in enumerate(["Track A", "Track B"], start=1):
        lesson = Lesson.objects.create(title=title, content="...")
        contents.append(
            CourseContent.objects.create(
                course=course,
                track=track,
                priority=priority,
                type="lesson",
                lesson=lesson,
                waiting_period=3600,
                is_published=True,
            )
        )
    return track, contents


def test_walk_stays_inside_a_track(branch):
    _, (track_a, track_b) = branch

    assert next_content(track_a) == track_b


def test_track_content_does_not_leak_into_the_spine_walk(branch, lessons):
    """Spine content must not walk into a branch it shares priorities with."""
    _, (track_a, _) = branch
    assert track_a.priority == lessons[0].priority

    assert next_content(lessons[0]) == lessons[1]


def test_exhausted_track_continues_at_its_merge_point(branch, lessons):
    _, (_, track_b) = branch

    assert next_content(track_b) == lessons[3]


def test_exhausted_track_steps_over_an_unpublished_merge_point(branch, lessons):
    lessons[3].is_published = False
    lessons[3].save()
    _, (_, track_b) = branch

    assert next_content(track_b) is None


def test_track_without_a_merge_point_ends_the_course(branch):
    track, (_, track_b) = branch
    track.merge_into = None
    track.save()

    assert next_content(track_b) is None


def test_nested_track_falls_back_to_its_parents_merge_point(db, course, branch, lessons):
    """A track that branches off a track, with no merge point of its own."""
    parent_track, _ = branch
    nested = ContentTrack.objects.create(course=course, name="Nested path", parent_track=parent_track)
    lesson = Lesson.objects.create(title="Nested", content="...")
    nested_content = CourseContent.objects.create(
        course=course,
        track=nested,
        priority=1,
        type="lesson",
        lesson=lesson,
        waiting_period=3600,
        is_published=True,
    )

    assert next_content(nested_content) == lessons[3]


def test_nested_track_prefers_its_own_merge_point(db, course, branch, lessons):
    parent_track, _ = branch
    nested = ContentTrack.objects.create(
        course=course,
        name="Nested path",
        parent_track=parent_track,
        merge_into=lessons[2],
    )
    lesson = Lesson.objects.create(title="Nested", content="...")
    nested_content = CourseContent.objects.create(
        course=course,
        track=nested,
        priority=1,
        type="lesson",
        lesson=lesson,
        waiting_period=3600,
        is_published=True,
    )

    assert next_content(nested_content) == lessons[2]


def test_a_merge_loop_ends_the_course_instead_of_spinning(db, course, lessons):
    """A malformed graph must terminate.

    `clean()` refuses to point a merge anywhere but outward, so this shape cannot be
    authored - it is written here with `.update()`, which skips validation the way a data
    migration or a raw SQL fix would. The guard exists for rows that arrive that way.
    """
    first_track = ContentTrack.objects.create(course=course, name="First")
    second_track = ContentTrack.objects.create(course=course, name="Second")
    contents = {}
    for name, track in (("first", first_track), ("second", second_track)):
        lesson = Lesson.objects.create(title=name, content="...")
        contents[name] = CourseContent.objects.create(
            course=course,
            track=track,
            priority=1,
            type="lesson",
            lesson=lesson,
            waiting_period=3600,
            is_published=False,
        )
    # Each track ends by merging into the other's unpublished content, so the walk is
    # handed straight back to a merge point it has already seen.
    ContentTrack.objects.filter(pk=first_track.pk).update(merge_into=contents["second"])
    ContentTrack.objects.filter(pk=second_track.pk).update(merge_into=contents["first"])

    assert next_content(contents["first"]) is None


def test_first_content_never_starts_on_a_track(db, course, branch, lessons):
    """A learner reaches a track by being routed onto it, never by starting there."""
    for spine_content in lessons:
        spine_content.is_published = False
        spine_content.save()

    assert first_content(course) is None


@pytest.fixture
def branch_point(db, course, lessons, quiz):
    """A quiz at spine priority 5, after the four lessons the `lessons` fixture publishes."""
    return CourseContent.objects.create(
        course=course, priority=5, type="quiz", quiz=quiz, waiting_period=60, is_published=True
    )


@pytest.fixture
def after_branch(db, course, branch_point):
    """Spine content at priority 6, where a track branching at the quiz can rejoin."""
    lesson = Lesson.objects.create(title="Wrap up", content="...")
    return CourseContent.objects.create(
        course=course, priority=6, type="lesson", lesson=lesson, waiting_period=60, is_published=True
    )


def track_with_contents(course, name, count, merge_into=None, published=True):
    track = ContentTrack.objects.create(course=course, name=name, merge_into=merge_into)
    contents = []
    for priority in range(1, count + 1):
        lesson = Lesson.objects.create(title=f"{name} {priority}", content="...")
        contents.append(
            CourseContent.objects.create(
                course=course,
                track=track,
                priority=priority,
                type="lesson",
                lesson=lesson,
                waiting_period=60,
                is_published=published,
            )
        )
    return track, contents


def test_an_outcome_routes_onto_the_matching_track(db, course, branch_point):
    passed_track, passed_contents = track_with_contents(course, "Advanced", 2)
    failed_track, failed_contents = track_with_contents(course, "Remedial", 2)
    ContentTransition.objects.create(
        source=branch_point, order=1, condition=TransitionCondition.PASSED, target=passed_track
    )
    ContentTransition.objects.create(
        source=branch_point, order=2, condition=TransitionCondition.FAILED, target=failed_track
    )

    assert next_content(branch_point, outcome=QuizOutcome(score=90, passed=True)) == passed_contents[0]
    assert next_content(branch_point, outcome=QuizOutcome(score=10, passed=False)) == failed_contents[0]


def test_the_first_matching_rule_wins(db, course, branch_point):
    high, high_contents = track_with_contents(course, "High", 1)
    any_score, any_contents = track_with_contents(course, "Any", 1)
    ContentTransition.objects.create(
        source=branch_point, order=1, condition=TransitionCondition.SCORE_GTE, threshold=80, target=high
    )
    ContentTransition.objects.create(
        source=branch_point, order=2, condition=TransitionCondition.DEFAULT, target=any_score
    )

    assert next_content(branch_point, outcome=QuizOutcome(score=95, passed=True)) == high_contents[0]
    assert next_content(branch_point, outcome=QuizOutcome(score=20, passed=False)) == any_contents[0]


def test_an_unmatched_outcome_falls_through_to_the_linear_walk(db, course, branch_point, after_branch):
    """A rule set with no default leaves the learner on their current track."""
    high, _ = track_with_contents(course, "High", 1)
    ContentTransition.objects.create(
        source=branch_point, order=1, condition=TransitionCondition.SCORE_GTE, threshold=80, target=high
    )

    assert next_content(branch_point, outcome=QuizOutcome(score=10, passed=False)) == after_branch


def test_content_without_rules_ignores_an_outcome(db, lessons):
    assert next_content(lessons[0], outcome=QuizOutcome(score=90, passed=True)) == lessons[1]


def test_rules_are_ignored_without_an_outcome(db, course, branch_point, after_branch):
    """A deadline passing or the inactivity job stepping along must not route anyone."""
    high, _ = track_with_contents(course, "High", 1)
    ContentTransition.objects.create(source=branch_point, order=1, condition=TransitionCondition.DEFAULT, target=high)

    assert next_content(branch_point) == after_branch


def test_routing_skips_unpublished_content_at_the_head_of_a_track(db, course, branch_point):
    track, contents = track_with_contents(course, "Advanced", 3)
    contents[0].is_published = False
    contents[0].save()
    ContentTransition.objects.create(source=branch_point, order=1, condition=TransitionCondition.DEFAULT, target=track)

    assert next_content(branch_point, outcome=QuizOutcome(score=90, passed=True)) == contents[1]


def test_routing_onto_an_empty_track_lands_on_its_merge_point(db, course, branch_point, after_branch):
    empty = ContentTrack.objects.create(course=course, name="Empty", merge_into=after_branch)
    ContentTransition.objects.create(source=branch_point, order=1, condition=TransitionCondition.DEFAULT, target=empty)

    assert next_content(branch_point, outcome=QuizOutcome(score=90, passed=True)) == after_branch


def test_routing_onto_a_terminal_track_ends_the_course(db, course, branch_point):
    terminal = ContentTrack.objects.create(course=course, name="Terminal")
    ContentTransition.objects.create(
        source=branch_point, order=1, condition=TransitionCondition.DEFAULT, target=terminal
    )

    assert next_content(branch_point, outcome=QuizOutcome(score=10, passed=False)) is None
