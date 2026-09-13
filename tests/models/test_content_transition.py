import pytest
from django.core.exceptions import ValidationError

from django_email_learning.models import (
    ContentTrack,
    ContentTransition,
    CourseContent,
    Lesson,
    Quiz,
    QuizOutcome,
    TransitionCondition,
)


@pytest.fixture
def spine(db, course, quiz):
    """A spine of lesson(1), quiz(2), lesson(3)."""
    contents = {}
    for priority, kind in ((1, "lesson"), (2, "quiz"), (3, "lesson")):
        if kind == "quiz":
            contents["quiz"] = CourseContent.objects.create(
                course=course, priority=priority, type="quiz", quiz=quiz, waiting_period=60, is_published=True
            )
        else:
            lesson = Lesson.objects.create(title=f"Lesson {priority}", content="...")
            contents[f"lesson{priority}"] = CourseContent.objects.create(
                course=course, priority=priority, type="lesson", lesson=lesson, waiting_period=60, is_published=True
            )
    return contents


@pytest.fixture
def remedial(db, course, spine):
    return ContentTrack.objects.create(course=course, name="Remedial", merge_into=spine["lesson3"])


def test_a_score_condition_needs_a_threshold(db, spine, remedial):
    with pytest.raises(ValidationError, match="needs a threshold"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.SCORE_GTE, target=remedial
        )


def test_a_non_score_condition_rejects_a_threshold(db, spine, remedial):
    with pytest.raises(ValidationError, match="Only a score condition"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.PASSED, threshold=50, target=remedial
        )


def test_a_quiz_condition_cannot_sit_on_a_lesson(db, spine, remedial):
    with pytest.raises(ValidationError, match="only be used on quiz content"):
        ContentTransition.objects.create(
            source=spine["lesson1"], order=1, condition=TransitionCondition.PASSED, target=remedial
        )


def test_a_default_condition_sits_on_any_content(db, spine, remedial):
    transition = ContentTransition.objects.create(
        source=spine["lesson1"], order=1, condition=TransitionCondition.DEFAULT, target=remedial
    )

    assert transition.pk


def test_a_target_must_belong_to_the_same_course(db, spine, imap_connection):
    from django_email_learning.models import Course

    other_course = Course.objects.create(
        title="Other", slug="other", imap_connection=imap_connection, organization_id=1
    )
    foreign_track = ContentTrack.objects.create(course=other_course, name="Foreign")

    with pytest.raises(ValidationError, match="same course"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.PASSED, target=foreign_track
        )


def test_content_cannot_route_onto_its_own_track(db, course, spine):
    track = ContentTrack.objects.create(course=course, name="Path", merge_into=spine["lesson3"])
    # Its own quiz: a course may not carry the same quiz twice.
    track_quiz = Quiz.objects.create(
        title="On-track quiz", required_score=70, selection_strategy="all", deadline_days=7
    )
    on_track = CourseContent.objects.create(
        course=course, track=track, priority=1, type="quiz", quiz=track_quiz, waiting_period=60
    )

    with pytest.raises(ValidationError, match="already on"):
        ContentTransition.objects.create(source=on_track, order=1, condition=TransitionCondition.PASSED, target=track)


def test_a_target_rejoining_before_the_branch_point_is_rejected(db, course, spine):
    """Routing at content 2 onto a track that rejoins at content 1 would loop forever."""
    backward = ContentTrack.objects.create(course=course, name="Backward", merge_into=spine["lesson1"])

    with pytest.raises(ValidationError, match="rejoins the course at or before"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.FAILED, target=backward
        )


def test_a_target_rejoining_at_the_branch_point_is_rejected(db, course, spine):
    onto_itself = ContentTrack.objects.create(course=course, name="Onto itself", merge_into=spine["quiz"])

    with pytest.raises(ValidationError, match="rejoins the course at or before"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.FAILED, target=onto_itself
        )


def test_a_track_that_ends_the_course_is_accepted(db, course, spine):
    """No merge point means the learner finishes there, which cannot loop."""
    terminal = ContentTrack.objects.create(course=course, name="Terminal")

    transition = ContentTransition.objects.create(
        source=spine["quiz"], order=1, condition=TransitionCondition.FAILED, target=terminal
    )

    assert transition.pk


def test_only_one_default_rule_per_content(db, spine, remedial, course):
    other = ContentTrack.objects.create(course=course, name="Other", merge_into=spine["lesson3"])
    ContentTransition.objects.create(
        source=spine["quiz"], order=1, condition=TransitionCondition.DEFAULT, target=remedial
    )

    with pytest.raises(ValidationError, match="single_default_transition_per_source"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=2, condition=TransitionCondition.DEFAULT, target=other
        )


def test_order_is_unique_per_content(db, spine, remedial, course):
    other = ContentTrack.objects.create(course=course, name="Other", merge_into=spine["lesson3"])
    ContentTransition.objects.create(
        source=spine["quiz"], order=1, condition=TransitionCondition.PASSED, target=remedial
    )

    with pytest.raises(ValidationError, match="Source and Order already exists"):
        ContentTransition.objects.create(
            source=spine["quiz"], order=1, condition=TransitionCondition.FAILED, target=other
        )


@pytest.mark.parametrize(
    "condition,threshold,score,passed,expected",
    [
        (TransitionCondition.PASSED, None, 90, True, True),
        (TransitionCondition.PASSED, None, 10, False, False),
        (TransitionCondition.FAILED, None, 10, False, True),
        (TransitionCondition.FAILED, None, 90, True, False),
        (TransitionCondition.SCORE_GTE, 80, 80, True, True),
        (TransitionCondition.SCORE_GTE, 80, 79, False, False),
        (TransitionCondition.SCORE_LT, 50, 49, False, True),
        (TransitionCondition.SCORE_LT, 50, 50, True, False),
        (TransitionCondition.DEFAULT, None, 0, False, True),
    ],
)
def test_condition_matching(db, spine, remedial, condition, threshold, score, passed, expected):
    transition = ContentTransition(
        source=spine["quiz"], order=1, condition=condition, threshold=threshold, target=remedial
    )

    assert transition.matches(QuizOutcome(score=score, passed=passed)) is expected
