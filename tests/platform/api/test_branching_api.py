import json

import pytest
from django.urls import reverse

from django_email_learning.models import ContentTrack, ContentTransition, CourseContent, Lesson, TransitionCondition


@pytest.fixture
def spine(db, course, course_lesson_content, course_quiz_content):
    course_quiz_content.is_published = True
    course_quiz_content.save()
    wrap_up = CourseContent.objects.create(
        course=course,
        priority=9,
        type="lesson",
        lesson=Lesson.objects.create(title="Wrap up", content="..."),
        waiting_period=60,
        is_published=True,
    )
    return {"lesson": course_lesson_content, "quiz": course_quiz_content, "wrap_up": wrap_up}


def tracks_url(course):
    return reverse(
        "django_email_learning:api_platform:content_tracks",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
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


def test_editor_creates_a_track(editor_client, course, spine):
    response = editor_client.post(
        tracks_url(course),
        data=json.dumps({"name": "Remedial", "merge_into_id": spine["wrap_up"].id}),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Remedial"
    assert ContentTrack.objects.filter(course=course, name="Remedial").exists()


def test_a_viewer_cannot_create_a_track(viewer_client, course, spine):
    response = viewer_client.post(
        tracks_url(course),
        data=json.dumps({"name": "Remedial"}),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_a_model_rule_surfaces_as_a_400(editor_client, course, spine):
    """A merge onto a sibling is refused by the model, not re-checked in the view."""
    sibling = ContentTrack.objects.create(course=course, name="Sibling")
    on_sibling = CourseContent.objects.create(
        course=course,
        track=sibling,
        priority=1,
        type="lesson",
        lesson=Lesson.objects.create(title="On sibling", content="..."),
        waiting_period=60,
        is_published=True,
    )

    response = editor_client.post(
        tracks_url(course),
        data=json.dumps({"name": "Other", "merge_into_id": on_sibling.id}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "main spine" in json.dumps(response.json())


def test_a_track_from_another_course_is_not_reachable(editor_client, course, spine, imap_connection):
    from django_email_learning.models import Course

    other = Course.objects.create(title="Other", slug="other", imap_connection=imap_connection, organization_id=1)
    foreign = ContentTrack.objects.create(course=other, name="Foreign")

    response = editor_client.post(
        tracks_url(course),
        data=json.dumps({"name": "Child", "parent_track_id": foreign.id}),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_editor_creates_and_lists_a_transition(editor_client, course, spine):
    track = ContentTrack.objects.create(course=course, name="Remedial", merge_into=spine["wrap_up"])

    created = editor_client.post(
        transitions_url(spine["quiz"]),
        data=json.dumps(
            {"order": 1, "condition": TransitionCondition.SCORE_LT.value, "threshold": 50, "target_id": track.id}
        ),
        content_type="application/json",
    )
    listed = editor_client.get(transitions_url(spine["quiz"]))

    assert created.status_code == 201
    assert listed.status_code == 200
    assert [t["condition"] for t in listed.json()["transitions"]] == [TransitionCondition.SCORE_LT.value]


def test_a_transition_targeting_another_courses_track_is_not_found(editor_client, course, spine, imap_connection):
    from django_email_learning.models import Course

    other = Course.objects.create(title="Other", slug="other", imap_connection=imap_connection, organization_id=1)
    foreign = ContentTrack.objects.create(course=other, name="Foreign")

    response = editor_client.post(
        transitions_url(spine["quiz"]),
        data=json.dumps({"order": 1, "condition": TransitionCondition.PASSED.value, "target_id": foreign.id}),
        content_type="application/json",
    )

    assert response.status_code == 404


def test_editor_deletes_a_transition(editor_client, course, spine):
    track = ContentTrack.objects.create(course=course, name="Remedial", merge_into=spine["wrap_up"])
    transition = ContentTransition.objects.create(
        source=spine["quiz"], order=1, condition=TransitionCondition.PASSED, target=track
    )

    url = reverse(
        "django_email_learning:api_platform:content_transition_detail",
        kwargs={
            "organization_id": course.organization_id,
            "course_id": course.id,
            "content_id": spine["quiz"].id,
            "transition_id": transition.id,
        },
    )
    response = editor_client.delete(url)

    assert response.status_code == 204
    assert not ContentTransition.objects.filter(id=transition.id).exists()
