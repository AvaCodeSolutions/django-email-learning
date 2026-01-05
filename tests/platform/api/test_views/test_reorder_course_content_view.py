from django.urls import reverse
import json
from django_email_learning.models import CourseContent


def test_reorder_course_contents_view_success(
    superadmin_client,
    course,
    course_lesson_content,
    course_quiz_content,
):
    url = reverse(
        "django_email_learning:api_platform:reorder_course_contents_view",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )

    assert course_lesson_content.priority == 1
    assert course_quiz_content.priority == 2

    ordered_content_ids = [
        content.id for content in [course_quiz_content, course_lesson_content]
    ]

    data = {"ordered_content_ids": ordered_content_ids}

    response = superadmin_client.post(
        url, json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 200

    lesson = CourseContent.objects.get(id=course_lesson_content.id)
    quiz = CourseContent.objects.get(id=course_quiz_content.id)

    assert lesson.priority == 2
    assert quiz.priority == 1


def test_reorder_course_contents_view_invalid_request(
    superadmin_client,
    course,
    course_lesson_content,
    course_quiz_content,
):
    url = reverse(
        "django_email_learning:api_platform:reorder_course_contents_view",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )

    ordered_content_ids = [course_lesson_content.id, course_quiz_content.id]

    data = {"ordered_content": ordered_content_ids}

    response = superadmin_client.post(
        url, json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 400


def test_viewer_cannot_reorder_course_contents(
    viewer_client,
    course,
    course_lesson_content,
    course_quiz_content,
):
    url = reverse(
        "django_email_learning:api_platform:reorder_course_contents_view",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )

    ordered_content_ids = [course_lesson_content.id, course_quiz_content.id]

    data = {"ordered_content_ids": ordered_content_ids}

    response = viewer_client.post(
        url, json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 403


def test_reorder_course_contents_view_nonexistent_course(
    superadmin_client,
):
    url = reverse(
        "django_email_learning:api_platform:reorder_course_contents_view",
        kwargs={"organization_id": 1, "course_id": 9999},
    )

    ordered_content_ids = [1, 2]

    data = {"ordered_content_ids": ordered_content_ids}

    response = superadmin_client.post(
        url, json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 404


def test_anonymous_user_cannot_reorder_course_contents(
    anonymous_client,
    course,
    course_lesson_content,
    course_quiz_content,
):
    url = reverse(
        "django_email_learning:api_platform:reorder_course_contents_view",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )

    ordered_content_ids = [course_lesson_content.id, course_quiz_content.id]

    data = {"ordered_content_ids": ordered_content_ids}

    response = anonymous_client.post(
        url, json.dumps(data), content_type="application/json"
    )

    assert response.status_code == 401
