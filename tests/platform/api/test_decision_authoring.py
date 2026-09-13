"""Authoring a decision point over the API: creating it, editing its answers, and routing them."""

import json
from types import SimpleNamespace

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DecisionOption,
    DecisionPoint,
    DecisionResponse,
    Lesson,
    TransitionCondition,
)


def contents_url(course):
    return reverse(
        "django_email_learning:api_platform:course_contents_reorder",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    ).removesuffix("reorder/")


def content_url(content):
    return f"{contents_url(content.course)}{content.id}/"


def transitions_url(content):
    return reverse(
        "django_email_learning:api_platform:content_transitions",
        kwargs={
            "organization_id": content.course.organization_id,
            "course_id": content.course_id,
            "content_id": content.id,
        },
    )


def post_json(client, url, data):
    return client.post(url, data=json.dumps(data), content_type="application/json")


def put_json(client, url, data):
    return client.put(url, data=json.dumps(data), content_type="application/json")


@pytest.fixture
def decision_course(db, course):
    """Spine: Pick your path (decision, 1), Wrap up (2), with a "Deeper" track rejoining at Wrap up."""
    decision = DecisionPoint.objects.create(title="Pick your path", prompt="Where next?")
    basics = DecisionOption.objects.create(decision=decision, text="Basics", order=1)
    deeper_dive = DecisionOption.objects.create(decision=decision, text="Deeper dive", order=2)
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=decision, waiting_period=3600, is_published=True
    )
    wrap_up = CourseContent.objects.create(
        course=course,
        priority=2,
        type="lesson",
        lesson=Lesson.objects.create(title="Wrap up", content="..."),
        waiting_period=3600,
        is_published=True,
    )
    deeper = ContentTrack.objects.create(course=course, name="Deeper", merge_into=wrap_up)
    return SimpleNamespace(
        course=course, content=content, basics=basics, deeper_dive=deeper_dive, wrap_up=wrap_up, deeper=deeper
    )


def new_decision(options):
    return {
        "waiting_period": {"period": 1, "type": "days"},
        "content": {
            "type": "decision",
            "title": "Pick your path",
            "prompt": "Where next?",
            "deadline_days": 0,
            "reminder_interval_days": 2,
            "options": options,
        },
    }


def test_creating_a_decision_point_saves_its_answers_in_order(editor_client, course):
    response = post_json(
        editor_client, contents_url(course), new_decision([{"text": "Basics"}, {"text": "Deeper dive"}])
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["type"] == "decision"
    assert [option["text"] for option in body["decision"]["options"]] == ["Basics", "Deeper dive"]
    assert CourseContent.objects.get(id=body["id"]).decision.reminder_interval_days == 2


def test_a_decision_point_needs_at_least_two_answers(editor_client, course):
    response = post_json(editor_client, contents_url(course), new_decision([{"text": "Only one"}]))

    assert response.status_code == 400
    assert not DecisionPoint.objects.exists()


def test_the_content_detail_carries_the_question_and_its_answers(editor_client, decision_course):
    d = decision_course

    body = editor_client.get(content_url(d.content)).json()

    assert body["decision"]["prompt"] == "Where next?"
    assert [(option["id"], option["text"]) for option in body["decision"]["options"]] == [
        (d.basics.id, "Basics"),
        (d.deeper_dive.id, "Deeper dive"),
    ]


def test_editing_the_answers_updates_adds_reorders_and_removes(editor_client, decision_course):
    d = decision_course
    ContentTransition.objects.create(
        source=d.content, order=1, condition=TransitionCondition.OPTION_SELECTED, option=d.basics, target=d.deeper
    )

    response = post_json(
        editor_client,
        content_url(d.content),
        {"decision": {"options": [{"id": d.deeper_dive.id, "text": "Go deeper"}, {"text": "Both"}]}},
    )

    assert response.status_code == 200, response.content
    options = response.json()["decision"]["options"]
    assert [(option["text"], option["order"]) for option in options] == [("Go deeper", 1), ("Both", 2)]
    assert options[0]["id"] == d.deeper_dive.id
    assert not DecisionOption.objects.filter(id=d.basics.id).exists()
    assert not ContentTransition.objects.filter(source=d.content).exists()


def test_an_answer_learners_have_chosen_cannot_be_removed(editor_client, decision_course, active_enrollment):
    d = decision_course
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=d.content)
    DecisionResponse.objects.create(delivery=delivery, option=d.basics)

    response = post_json(
        editor_client,
        content_url(d.content),
        {"decision": {"options": [{"id": d.deeper_dive.id, "text": "Deeper dive"}, {"text": "Both"}]}},
    )

    assert response.status_code == 409
    assert list(d.content.decision.options.values_list("text", flat=True)) == ["Basics", "Deeper dive"]


def test_an_answer_of_another_decision_point_cannot_be_edited_through_this_one(editor_client, decision_course):
    d = decision_course
    elsewhere = DecisionOption.objects.create(
        decision=DecisionPoint.objects.create(title="Another question", prompt="?"), text="Elsewhere", order=1
    )

    response = post_json(
        editor_client,
        content_url(d.content),
        {"decision": {"options": [{"id": elsewhere.id, "text": "Taken over"}, {"text": "Both"}]}},
    )

    assert response.status_code == 409
    elsewhere.refresh_from_db()
    assert elsewhere.text == "Elsewhere"


def test_rules_route_answers_onto_tracks(editor_client, decision_course):
    d = decision_course

    response = put_json(
        editor_client,
        transitions_url(d.content),
        {
            "transitions": [
                {"condition": "option_selected", "option_id": d.deeper_dive.id, "target_id": d.deeper.id},
                {"condition": "default", "target_id": d.deeper.id},
            ]
        },
    )

    assert response.status_code == 200, response.content
    first, otherwise = response.json()["transitions"]
    assert (first["option_id"], first["option_text"]) == (d.deeper_dive.id, "Deeper dive")
    assert (otherwise["option_id"], otherwise["option_text"]) == (None, None)


def test_the_contents_listing_names_the_answer_each_rule_matches(editor_client, decision_course):
    d = decision_course
    ContentTransition.objects.create(
        source=d.content, order=1, condition=TransitionCondition.OPTION_SELECTED, option=d.deeper_dive, target=d.deeper
    )

    body = editor_client.get(contents_url(d.course)).json()

    assert body["transitions"][0]["option_text"] == "Deeper dive"
    assert next(item for item in body["course_contents"] if item["id"] == d.content.id)["type"] == "decision"


def test_a_rule_cannot_route_on_another_decision_points_answer(editor_client, decision_course):
    d = decision_course
    elsewhere = DecisionOption.objects.create(
        decision=DecisionPoint.objects.create(title="Another question", prompt="?"), text="Elsewhere", order=1
    )

    response = put_json(
        editor_client,
        transitions_url(d.content),
        {"transitions": [{"condition": "option_selected", "option_id": elsewhere.id, "target_id": d.deeper.id}]},
    )

    assert response.status_code == 404
    assert not ContentTransition.objects.exists()


def test_an_answer_rule_without_an_answer_is_refused(editor_client, decision_course):
    d = decision_course

    response = put_json(
        editor_client,
        transitions_url(d.content),
        {"transitions": [{"condition": "option_selected", "target_id": d.deeper.id}]},
    )

    assert response.status_code == 400
    assert "needs the answer it matches" in " ".join(response.json()["error"])
    assert not ContentTransition.objects.exists()


def test_a_quiz_rule_on_a_decision_point_is_refused(editor_client, decision_course):
    d = decision_course

    response = put_json(
        editor_client,
        transitions_url(d.content),
        {"transitions": [{"condition": "failed", "target_id": d.deeper.id}]},
    )

    assert response.status_code == 400
    assert not ContentTransition.objects.exists()
