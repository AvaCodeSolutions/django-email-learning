"""The authoring side of branching: the data the content table renders, reordering and
moving content, editing tracks, and replacing a quiz's rule set in one request.
"""

import json
from types import SimpleNamespace

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ContentTrack,
    ContentTransition,
    Course,
    CourseContent,
    Lesson,
    Quiz,
    TransitionCondition,
)


def make_lesson(course, priority, track=None, title=None):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title or f"Lesson {priority} {track}", content="..."),
        waiting_period=3600,
        is_published=True,
    )


@pytest.fixture
def branching_course(db, course):
    """Spine: Intro(1), Checkpoint quiz(2), Practice(3), Wrap up(4).

    Failing the checkpoint routes onto "Remedial", two lessons long, which rejoins at Wrap up.
    """
    spine1 = make_lesson(course, 1, title="Intro")
    quiz = Quiz.objects.create(title="Checkpoint", required_score=70, selection_strategy="all", deadline_days=0)
    checkpoint = CourseContent.objects.create(
        course=course, priority=2, type="quiz", quiz=quiz, waiting_period=3600, is_published=True
    )
    spine3 = make_lesson(course, 3, title="Practice")
    spine4 = make_lesson(course, 4, title="Wrap up")
    remedial = ContentTrack.objects.create(course=course, name="Remedial", merge_into=spine4)
    remedial1 = make_lesson(course, 1, remedial, title="Remedial 1")
    remedial2 = make_lesson(course, 2, remedial, title="Remedial 2")
    rule = ContentTransition.objects.create(
        source=checkpoint, order=1, condition=TransitionCondition.FAILED, target=remedial
    )
    return SimpleNamespace(
        course=course,
        spine1=spine1,
        checkpoint=checkpoint,
        spine3=spine3,
        spine4=spine4,
        remedial=remedial,
        remedial1=remedial1,
        remedial2=remedial2,
        rule=rule,
    )


def reorder_url(course):
    return reverse(
        "django_email_learning:api_platform:course_contents_reorder",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )


def contents_url(course):
    return reorder_url(course).removesuffix("reorder/")


def content_url(content):
    return f"{contents_url(content.course)}{content.id}/"


def track_url(track):
    return reverse(
        "django_email_learning:api_platform:content_track_detail",
        kwargs={"organization_id": track.course.organization_id, "course_id": track.course_id, "track_id": track.id},
    )


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


def test_the_contents_listing_carries_the_branching_structure(editor_client, branching_course):
    b = branching_course

    response = editor_client.get(contents_url(b.course))

    assert response.status_code == 200
    body = response.json()
    by_id = {content["id"]: content for content in body["course_contents"]}
    assert by_id[b.remedial1.id]["track_id"] == b.remedial.id
    assert by_id[b.spine1.id]["track_id"] is None
    assert body["tracks"] == [
        {"id": b.remedial.id, "name": "Remedial", "parent_track_id": None, "merge_into_id": b.spine4.id}
    ]
    assert [(rule["source_id"], rule["condition"], rule["target_id"]) for rule in body["transitions"]] == [
        (b.checkpoint.id, "failed", b.remedial.id)
    ]


def test_content_detail_says_whether_it_is_a_branch_point(editor_client, branching_course):
    b = branching_course

    assert editor_client.get(content_url(b.checkpoint)).json()["is_branch_point"] is True
    assert editor_client.get(content_url(b.spine1)).json()["is_branch_point"] is False


def test_reordering_a_track_renumbers_only_that_track(editor_client, branching_course):
    b = branching_course

    response = post_json(
        editor_client, reorder_url(b.course), {"ordered_content_ids": [b.remedial2.id, b.remedial1.id]}
    )

    assert response.status_code == 200
    for content in (b.remedial1, b.remedial2, b.spine1):
        content.refresh_from_db()
    assert (b.remedial2.priority, b.remedial1.priority) == (1, 2)
    assert b.spine1.priority == 1


def test_a_reorder_spanning_two_tracks_is_refused(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, reorder_url(b.course), {"ordered_content_ids": [b.remedial1.id, b.spine1.id]})

    assert response.status_code == 409
    assert "one track" in response.json()["error"]
    b.remedial1.refresh_from_db()
    b.spine1.refresh_from_db()
    assert (b.remedial1.priority, b.spine1.priority) == (1, 1)


def test_a_reorder_moving_a_merge_point_behind_its_branch_point_is_refused(editor_client, branching_course):
    """Wrap up would come before the checkpoint that routes onto a track rejoining there."""
    b = branching_course

    response = post_json(
        editor_client,
        reorder_url(b.course),
        {"ordered_content_ids": [b.spine4.id, b.spine1.id, b.checkpoint.id, b.spine3.id]},
    )

    assert response.status_code == 409
    assert "rejoins the course at or before" in response.json()["error"]
    b.spine4.refresh_from_db()
    b.checkpoint.refresh_from_db()
    assert (b.spine4.priority, b.checkpoint.priority) == (4, 2)


def test_moving_content_onto_a_track_puts_it_at_the_end(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, content_url(b.spine3), {"track_id": b.remedial.id})

    assert response.status_code == 200
    b.spine3.refresh_from_db()
    assert (b.spine3.track_id, b.spine3.priority) == (b.remedial.id, 3)


def test_moving_content_back_to_the_main_spine(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, content_url(b.remedial1), {"track_id": None})

    assert response.status_code == 200
    b.remedial1.refresh_from_db()
    assert (b.remedial1.track_id, b.remedial1.priority) == (None, 5)


def test_a_move_that_would_break_routing_is_refused(editor_client, branching_course):
    """Wrap up is where Remedial rejoins, and a track cannot rejoin at its own content."""
    b = branching_course

    response = post_json(editor_client, content_url(b.spine4), {"track_id": b.remedial.id})

    assert response.status_code == 409
    b.spine4.refresh_from_db()
    assert (b.spine4.track_id, b.spine4.priority) == (None, 4)


def test_renaming_a_track_leaves_its_merge_point_alone(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, track_url(b.remedial), {"name": "Catch-up"})

    assert response.status_code == 200
    b.remedial.refresh_from_db()
    assert (b.remedial.name, b.remedial.merge_into_id) == ("Catch-up", b.spine4.id)


def test_re_pointing_a_merge_point_behind_the_branch_point_is_refused(editor_client, branching_course):
    """The track's own checks pass - only the rule routing onto it sees the loop."""
    b = branching_course

    response = post_json(editor_client, track_url(b.remedial), {"merge_into_id": b.spine1.id})

    assert response.status_code == 400
    assert any("rejoins the course at or before" in message for message in response.json()["error"])
    b.remedial.refresh_from_db()
    assert b.remedial.merge_into_id == b.spine4.id


def test_clearing_the_merge_point_makes_the_track_end_the_course(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, track_url(b.remedial), {"merge_into_id": None})

    assert response.status_code == 200
    b.remedial.refresh_from_db()
    assert b.remedial.merge_into_id is None


def test_a_populated_track_cannot_be_deleted(editor_client, branching_course):
    b = branching_course

    response = editor_client.delete(track_url(b.remedial))

    assert response.status_code == 409
    assert ContentTrack.objects.filter(id=b.remedial.id).exists()


def test_an_empty_track_is_deleted(editor_client, branching_course):
    empty = ContentTrack.objects.create(course=branching_course.course, name="Empty")

    response = editor_client.delete(track_url(empty))

    assert response.status_code == 204
    assert not ContentTrack.objects.filter(id=empty.id).exists()


def test_a_viewer_cannot_change_a_track(viewer_client, branching_course):
    response = post_json(viewer_client, track_url(branching_course.remedial), {"name": "Nope"})

    assert response.status_code == 403


def test_replacing_the_rule_set_keeps_the_order_given(editor_client, branching_course):
    b = branching_course
    advanced = ContentTrack.objects.create(course=b.course, name="Advanced", merge_into=b.spine4)

    response = put_json(
        editor_client,
        transitions_url(b.checkpoint),
        {
            "transitions": [
                {"condition": "score_lt", "threshold": 50, "target_id": b.remedial.id},
                {"condition": "default", "target_id": advanced.id},
            ]
        },
    )

    assert response.status_code == 200
    saved = list(b.checkpoint.transitions.order_by("order").values_list("order", "condition", "threshold", "target_id"))
    assert saved == [(1, "score_lt", 50, b.remedial.id), (2, "default", None, advanced.id)]


def test_an_otherwise_rule_must_come_last(editor_client, branching_course):
    b = branching_course

    response = put_json(
        editor_client,
        transitions_url(b.checkpoint),
        {
            "transitions": [
                {"condition": "default", "target_id": b.remedial.id},
                {"condition": "passed", "target_id": b.remedial.id},
            ]
        },
    )

    assert response.status_code == 400
    assert list(b.checkpoint.transitions.values_list("condition", flat=True)) == ["failed"]


def test_one_invalid_rule_leaves_the_existing_set_untouched(editor_client, branching_course):
    b = branching_course
    backward = ContentTrack.objects.create(course=b.course, name="Backward", merge_into=b.spine1)

    response = put_json(
        editor_client,
        transitions_url(b.checkpoint),
        {
            "transitions": [
                {"condition": "passed", "target_id": b.remedial.id},
                {"condition": "failed", "target_id": backward.id},
            ]
        },
    )

    assert response.status_code == 400
    assert list(b.checkpoint.transitions.values_list("condition", "target_id")) == [("failed", b.remedial.id)]


def test_an_empty_rule_set_stops_the_content_branching(editor_client, branching_course):
    b = branching_course

    response = put_json(editor_client, transitions_url(b.checkpoint), {"transitions": []})

    assert response.status_code == 200
    assert not b.checkpoint.transitions.exists()


def test_a_rule_targeting_another_courses_track_is_not_found(editor_client, branching_course, imap_connection):
    other = Course.objects.create(title="Other", slug="other", imap_connection=imap_connection, organization_id=1)
    foreign = ContentTrack.objects.create(course=other, name="Foreign")

    response = put_json(
        editor_client,
        transitions_url(branching_course.checkpoint),
        {"transitions": [{"condition": "passed", "target_id": foreign.id}]},
    )

    assert response.status_code == 404


def test_a_viewer_cannot_replace_rules(viewer_client, branching_course):
    response = put_json(viewer_client, transitions_url(branching_course.checkpoint), {"transitions": []})

    assert response.status_code == 403


def new_lesson_payload(**extra):
    return {
        "content": {"type": "lesson", "title": "New lesson", "content": "<p>Body</p>"},
        "waiting_period": {"period": 1, "type": "days"},
        **extra,
    }


def test_creating_content_on_a_track_numbers_it_within_that_track(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, contents_url(b.course), new_lesson_payload(track_id=b.remedial.id))

    assert response.status_code == 201
    created = CourseContent.objects.get(id=response.json()["id"])
    assert (created.track_id, created.priority) == (b.remedial.id, 3)


def test_creating_content_without_a_track_puts_it_at_the_end_of_the_main_spine(editor_client, branching_course):
    b = branching_course

    response = post_json(editor_client, contents_url(b.course), new_lesson_payload())

    assert response.status_code == 201
    created = CourseContent.objects.get(id=response.json()["id"])
    assert (created.track_id, created.priority) == (None, 5)


def test_creating_content_on_another_courses_track_is_not_found(editor_client, branching_course, imap_connection):
    other = Course.objects.create(title="Other", slug="other", imap_connection=imap_connection, organization_id=1)
    foreign = ContentTrack.objects.create(course=other, name="Foreign")

    response = post_json(editor_client, contents_url(branching_course.course), new_lesson_payload(track_id=foreign.id))

    assert response.status_code == 404
    assert not Lesson.objects.filter(title="New lesson").exists()
