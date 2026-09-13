"""DecisionPoint: a one-question choice whose answer, rather than a score, routes the learner."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DecisionOption,
    DecisionOutcome,
    DecisionPoint,
    DecisionResponse,
    DeliverySchedule,
    Lesson,
    TransitionCondition,
)
from django_email_learning.services import content_sequence_service


def make_decision(title="Pick your path", options=("Basics", "Deeper dive"), deadline_days=0):
    decision = DecisionPoint.objects.create(title=title, prompt="Where next?", deadline_days=deadline_days)
    for order, text in enumerate(options, start=1):
        DecisionOption.objects.create(decision=decision, text=text, order=order)
    return decision


def make_lesson(course, priority, track=None, title="Lesson"):
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
def decision_course(db, course):
    """Spine: Pick your path (decision, 1), Wrap up (2). "Deeper" is one lesson and rejoins at Wrap up."""
    decision = make_decision()
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=decision, waiting_period=3600, is_published=True
    )
    wrap_up = make_lesson(course, 2, title="Wrap up")
    deeper = ContentTrack.objects.create(course=course, name="Deeper", merge_into=wrap_up)
    deeper_lesson = make_lesson(course, 1, deeper, title="Deeper lesson")
    basics, deeper_dive = decision.options.all()
    return SimpleNamespace(
        course=course,
        content=content,
        wrap_up=wrap_up,
        deeper=deeper,
        deeper_lesson=deeper_lesson,
        basics=basics,
        deeper_dive=deeper_dive,
    )


def answer_rule(d, option, order=1):
    return ContentTransition.objects.create(
        source=d.content, order=order, condition=TransitionCondition.OPTION_SELECTED, option=option, target=d.deeper
    )


def test_decision_content_takes_its_title_and_deadline_from_the_decision_point(db, course):
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=make_decision(deadline_days=3), waiting_period=3600
    )

    assert content.title == "Pick your path"
    assert content.deadline_days == 3
    assert str(content) == "1 - Decision: Pick your path"
    assert content.is_blocking is False


def test_decision_content_requires_a_decision_point(db, course):
    with pytest.raises(ValidationError, match="Decision must be provided"):
        CourseContent.objects.create(course=course, priority=1, type="decision", waiting_period=3600)


def test_a_decision_point_is_used_once_per_course(db, course):
    decision = make_decision()
    CourseContent.objects.create(course=course, priority=1, type="decision", decision=decision, waiting_period=3600)

    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=2, type="decision", decision=decision, waiting_period=3600)


def test_an_answer_rule_matches_only_its_answer(decision_course):
    rule = answer_rule(decision_course, decision_course.deeper_dive)

    assert rule.matches(DecisionOutcome(option_id=decision_course.deeper_dive.id))
    assert not rule.matches(DecisionOutcome(option_id=decision_course.basics.id))


def test_an_otherwise_rule_matches_any_answer(decision_course):
    rule = ContentTransition.objects.create(
        source=decision_course.content, order=1, condition=TransitionCondition.DEFAULT, target=decision_course.deeper
    )

    assert rule.matches(DecisionOutcome(option_id=decision_course.basics.id))


def test_an_answer_rule_needs_an_answer(decision_course):
    with pytest.raises(ValidationError, match="needs the answer it matches"):
        ContentTransition.objects.create(
            source=decision_course.content,
            order=1,
            condition=TransitionCondition.OPTION_SELECTED,
            target=decision_course.deeper,
        )


def test_an_answer_rule_cannot_match_another_decision_points_answer(decision_course):
    elsewhere = make_decision(title="Another question").options.first()

    with pytest.raises(ValidationError, match="must belong to this decision point"):
        answer_rule(decision_course, elsewhere)


def test_an_answer_rule_can_only_sit_on_a_decision_point(decision_course, quiz):
    quiz_content = CourseContent.objects.create(
        course=decision_course.course, priority=3, type="quiz", quiz=quiz, waiting_period=3600
    )

    with pytest.raises(ValidationError, match="can only be used on a decision point"):
        ContentTransition.objects.create(
            source=quiz_content,
            order=1,
            condition=TransitionCondition.OPTION_SELECTED,
            option=decision_course.basics,
            target=decision_course.deeper,
        )


def test_a_quiz_condition_cannot_sit_on_a_decision_point(decision_course):
    with pytest.raises(ValidationError, match="can only be used on quiz content"):
        ContentTransition.objects.create(
            source=decision_course.content, order=1, condition=TransitionCondition.FAILED, target=decision_course.deeper
        )


def test_only_an_answer_rule_takes_an_answer(decision_course):
    with pytest.raises(ValidationError, match="Only an answer condition takes an answer"):
        ContentTransition.objects.create(
            source=decision_course.content,
            order=1,
            condition=TransitionCondition.DEFAULT,
            option=decision_course.basics,
            target=decision_course.deeper,
        )


def test_the_chosen_answer_selects_the_next_content(decision_course):
    d = decision_course
    answer_rule(d, d.deeper_dive)

    assert (
        content_sequence_service.next_content(d.content, DecisionOutcome(option_id=d.deeper_dive.id)) == d.deeper_lesson
    )
    assert content_sequence_service.next_content(d.content, DecisionOutcome(option_id=d.basics.id)) == d.wrap_up
    assert content_sequence_service.next_content(d.content) == d.wrap_up


def test_removing_an_answer_removes_the_rules_on_it(decision_course):
    rule = answer_rule(decision_course, decision_course.deeper_dive)

    decision_course.deeper_dive.delete()

    assert not ContentTransition.objects.filter(id=rule.id).exists()


def test_an_answer_learners_chose_cannot_be_deleted(decision_course, active_enrollment):
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=decision_course.content)
    DecisionResponse.objects.create(delivery=delivery, option=decision_course.basics)

    with pytest.raises(ProtectedError):
        decision_course.basics.delete()


def test_a_delivery_takes_one_answer(decision_course, active_enrollment):
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=decision_course.content)
    DecisionResponse.objects.create(delivery=delivery, option=decision_course.basics)

    with pytest.raises(ValidationError):
        DecisionResponse.objects.create(delivery=delivery, option=decision_course.deeper_dive)


def test_an_answer_must_come_from_the_delivered_decision_point(decision_course, active_enrollment):
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=decision_course.content)
    elsewhere = make_decision(title="Another question").options.first()

    with pytest.raises(ValidationError, match="must belong to this delivery"):
        DecisionResponse.objects.create(delivery=delivery, option=elsewhere)


def test_a_course_branching_on_a_decision_hides_learner_progress(decision_course, active_enrollment):
    answer_rule(decision_course, decision_course.deeper_dive)

    assert decision_course.course.has_branching()
    assert active_enrollment.learner_progress_percentage() is None


def test_a_decision_delivery_links_to_the_decision_page(decision_course, active_enrollment):
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=decision_course.content)
    schedule = DeliverySchedule.objects.create(delivery=delivery)

    link = schedule.generate_link()

    assert f"{reverse('django_email_learning:personalised:decision_public_view')}?token=" in link


def test_a_decision_with_a_deadline_is_reminded_before_it(db, course, active_enrollment):
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=make_decision(deadline_days=3), waiting_period=3600
    )
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=content)

    assert delivery.calculate_remind_at() is not None
