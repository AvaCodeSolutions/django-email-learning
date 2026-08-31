import json

import pytest
from django.urls import reverse

from django_email_learning.models import (
    ContentDelivery,
    Course,
    CourseContent,
    CourseContentType,
    Lesson,
    Organization,
)

LESSON_TITLE = "Introduction to Python"
LESSON_CONTENT = "Welcome to the Python course!"


def get_url() -> str:
    return reverse(
        "django_email_learning:api_platform:course_contents_list",
        kwargs={"organization_id": 1, "course_id": 1},
    )


def single_content_url(course_content_id: int, course_id: int, organization_id: int = 1) -> str:
    return reverse(
        "django_email_learning:api_platform:course_contents_detail",
        kwargs={
            "organization_id": organization_id,
            "course_id": course_id,
            "course_content_id": course_content_id,
        },
    )


def valid_create_course_payload(
    title: str = "Python Course",
    slug: str = "python",
    description: str = "A beginner's course on Python programming.",
) -> dict:
    return {
        "title": title,
        "slug": slug,
        "description": description,
        "imap_connection_id": None,
        "language": "en",
    }


@pytest.fixture()
def create_course(superadmin_client):
    url = reverse(
        "django_email_learning:api_platform:courses_list",
        kwargs={"organization_id": 1},
    )
    payload = valid_create_course_payload()
    superadmin_client.post(url, json.dumps(payload), content_type="application/json")


def test_create_course_lesson_content(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    data = response.json()
    assert "lesson" in data
    assert data["id"] is not None
    assert data["lesson"]["id"] is not None
    assert data["lesson"]["title"] == LESSON_TITLE
    assert data["lesson"]["content"] == LESSON_CONTENT
    assert data["is_published"] is False
    assert data["type"] == "lesson"
    assert data["priority"] == 1
    assert data["waiting_period"] == {"period": 2, "type": "days"}


def test_create_lesson_content_strips_script_tag_but_keeps_allowed_formatting(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": "<p>Hello <strong>world</strong></p><script>alert(document.cookie)</script>",
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    content = response.json()["lesson"]["content"]
    assert "<script>" not in content
    assert "<strong>world</strong>" in content


def test_update_lesson_content_strips_script_tag(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"lesson": {"content": '<p>Updated</p><img src=x onerror="alert(1)">'}}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    assert "onerror" not in response.json()["lesson"]["content"]


@pytest.mark.parametrize("title,content", [(None, LESSON_CONTENT), (LESSON_TITLE, None)])
def test_validate_lesson_content(superadmin_client, create_course, title, content):
    url = get_url()
    payload = {
        "content": {
            "title": title,
            "content": content,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }

    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


def test_viewer_can_not_create_course_content(viewer_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response = viewer_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 403


def test_anonymous_user_cannot_create_course_content(anonymous_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response = anonymous_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 401


def test_content_with_same_priority_cannot_be_created(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response1 = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response1.status_code == 201

    response2 = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response2.status_code == 400
    assert "error" in response2.json()


def test_create_quiz_content(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz 1",
            "required_score": 70,
            "selection_strategy": "all",
            "deadline_days": 14,
            "limited_attempts": False,
            "is_blocking": False,
            "questions": [
                {
                    "text": "What is Python?",
                    "priority": 1,
                    "answers": [
                        {"text": "A programming language", "is_correct": True},
                        {"text": "A snake", "is_correct": False},
                    ],
                },
                {
                    "text": "Which of these is a Python data type?",
                    "priority": 2,
                    "answers": [
                        {"text": "List", "is_correct": True},
                        {"text": "Car", "is_correct": False},
                    ],
                },
            ],
        },
        "priority": 2,
        "waiting_period": {"period": 1, "type": "hours"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    data = response.json()
    assert "quiz" in data
    assert data["id"] is not None
    assert data["quiz"]["id"] is not None
    assert data["type"] == "quiz"
    assert data["is_published"] is False
    assert data["priority"] == 2
    assert data["waiting_period"] == {"period": 1, "type": "hours"}
    assert data["quiz"]["title"] == "Quiz 1"
    assert data["quiz"]["required_score"] == 70
    assert data["quiz"]["selection_strategy"] == "all"
    assert data["quiz"]["limited_attempts"] is False
    assert data["quiz"]["is_blocking"] is False
    assert data["quiz"]["deadline_days"] == 14
    assert len(data["quiz"]["questions"]) == 2
    assert len(data["quiz"]["questions"][0]["answers"]) == 2
    assert len(data["quiz"]["questions"][1]["answers"]) == 2


def test_create_assignment_content(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "type": "assignment",
            "title": "Assignment 1",
            "description": "Submit your first project draft.",
            "is_blocking": True,
            "deadline_days": 10,
            "requires_text_submission": True,
            "requires_file_submission": True,
        },
        "priority": 3,
        "waiting_period": {"period": 6, "type": "hours"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["type"] == "assignment"
    assert data["priority"] == 3
    assert data["waiting_period"] == {"period": 6, "type": "hours"}
    assert data["is_published"] is False
    assert data["assignment"]["id"] is not None
    assert data["assignment"]["title"] == "Assignment 1"
    assert data["assignment"]["description"] == "Submit your first project draft."
    assert data["assignment"]["is_blocking"] is True
    assert data["assignment"]["deadline_days"] == 10
    assert data["assignment"]["requires_text_submission"] is True
    assert data["assignment"]["requires_file_submission"] is True


def test_invalid_quiz_content_missing_questions(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz without questions",
            "required_score": 70,
            "questions": [],
        },
        "priority": 2,
        "waiting_period": {"period": 1, "type": "hours"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


def test_invalid_quiz_content_insufficient_answers(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz with insufficient answers",
            "required_score": 70,
            "questions": [
                {
                    "text": "What is Python?",
                    "priority": 1,
                    "answers": [
                        {"text": "A programming language", "is_correct": True},
                    ],
                }
            ],
        },
        "priority": 2,
        "waiting_period": {"period": 1, "type": "hours"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


def test_invalid_quiz_content_no_correct_answer(superadmin_client, create_course):
    url = get_url()
    payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz with no correct answer",
            "required_score": 70,
            "questions": [
                {
                    "text": "What is Python?",
                    "priority": 1,
                    "answers": [
                        {"text": "A programming language", "is_correct": False},
                        {"text": "A snake", "is_correct": False},
                    ],
                }
            ],
        },
        "priority": 2,
        "waiting_period": {"period": 1, "type": "hours"},
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize("client", ["superadmin", "editor", "viewer"], indirect=["client"])
def test_list_course_content_access(client, create_course):
    url = get_url()
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["course_contents"], list)
    assert len(data["course_contents"]) == 0


def test_anonymous_user_cannot_list_course_content(anonymous_client, create_course):
    url = get_url()
    response = anonymous_client.get(url)
    assert response.status_code == 401


def test_list_course_content_with_existing_contents(superadmin_client, create_course):
    url = get_url()
    # Create a lesson content
    lesson_payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    superadmin_client.post(url, json.dumps(lesson_payload), content_type="application/json")

    # Create a quiz content
    quiz_payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz 1",
            "required_score": 70,
            "selection_strategy": "random",
            "deadline_days": 14,
            "is_blocking": False,
            "reminder_interval_days": 2,
            "questions": [
                {
                    "text": "What is Python?",
                    "priority": 1,
                    "answers": [
                        {"text": "A programming language", "is_correct": True},
                        {"text": "A snake", "is_correct": False},
                    ],
                }
            ],
        },
        "priority": 2,
        "waiting_period": {"period": 1, "type": "hours"},
    }
    superadmin_client.post(url, json.dumps(quiz_payload), content_type="application/json")

    # Now list the course contents
    response = superadmin_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["course_contents"], list)
    assert len(data["course_contents"]) == 2
    assert data["course_contents"][0]["type"] == "lesson"
    assert data["course_contents"][1]["type"] == "quiz"
    assert data["course_contents"][0]["priority"] == 1
    assert data["course_contents"][1]["priority"] == 2
    assert data["course_contents"][0]["id"] is not None
    assert data["course_contents"][1]["id"] is not None
    assert data["course_contents"][0]["title"] == LESSON_TITLE
    assert data["course_contents"][1]["title"] == "Quiz 1"
    assert data["course_contents"][0]["waiting_period"] == {"period": 2, "type": "days"}
    assert data["course_contents"][1]["waiting_period"] == {
        "period": 1,
        "type": "hours",
    }
    assert "lesson" not in data["course_contents"][0]
    assert "quiz" not in data["course_contents"][1]


def test_delete_course_content(superadmin_client, create_course):
    url = get_url()
    # Create a lesson content
    lesson_payload = {
        "content": {
            "title": LESSON_TITLE,
            "content": LESSON_CONTENT,
            "type": "lesson",
        },
        "priority": 1,
        "waiting_period": {"period": 2, "type": "days"},
    }
    response = superadmin_client.post(url, json.dumps(lesson_payload), content_type="application/json")
    assert response.status_code == 201
    data = response.json()
    course_content_id = data["id"]

    # Delete the created course content
    delete_url = reverse(
        "django_email_learning:api_platform:course_contents_detail",
        kwargs={
            "organization_id": 1,
            "course_id": 1,
            "course_content_id": course_content_id,
        },
    )
    contents_response = superadmin_client.get(url)
    assert contents_response.status_code == 200
    assert len(contents_response.json()["course_contents"]) == 1

    delete_response = superadmin_client.delete(delete_url)
    assert delete_response.status_code == 200

    # Verify that the course content is deleted
    contents_response_after_delete = superadmin_client.get(url)
    assert contents_response_after_delete.status_code == 200
    assert len(contents_response_after_delete.json()["course_contents"]) == 0
    get_response = superadmin_client.delete(delete_url)
    assert get_response.status_code == 404


def test_delete_course_content_with_delivery_returns_409(editor_client, course_lesson_content, enrollment):
    ContentDelivery.objects.create(enrollment=enrollment, course_content=course_lesson_content)
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )

    response = editor_client.delete(url)

    assert response.status_code == 409
    assert "Unpublish it instead" in response.json()["error"]
    assert CourseContent.objects.filter(id=course_lesson_content.id).exists()


def test_viewer_cannot_delete_course_content(viewer_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    response = viewer_client.delete(url)
    assert response.status_code == 403


def test_anonymous_user_cannot_delete_course_content(anonymous_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    response = anonymous_client.delete(url)
    assert response.status_code == 401


def test_get_course_content(viewer_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    get_response = viewer_client.get(url)
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == course_lesson_content.id
    assert get_data["type"] == "lesson"
    assert get_data["priority"] == 1
    assert get_data["waiting_period"] == {"period": 1, "type": "hours"}
    assert get_data["lesson"]["title"] == course_lesson_content.lesson.title
    assert get_data["lesson"]["content"] == course_lesson_content.lesson.content


def test_get_course_content_assignment_response_check(viewer_client, course_assignment_content):
    url = single_content_url(
        course_content_id=course_assignment_content.id,
        course_id=course_assignment_content.course.id,
        organization_id=course_assignment_content.course.organization.id,
    )
    response = viewer_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_assignment_content.id
    assert data["type"] == "assignment"
    assert data["priority"] == course_assignment_content.priority
    assert data["waiting_period"] == {"period": 2, "type": "hours"}
    assert data["assignment"]["id"] == course_assignment_content.assignment.id
    assert data["assignment"]["title"] == course_assignment_content.assignment.title
    assert data["assignment"]["description"] == course_assignment_content.assignment.description
    assert data["assignment"]["is_blocking"] == course_assignment_content.assignment.is_blocking
    assert data["assignment"]["deadline_days"] == course_assignment_content.assignment.deadline_days
    assert (
        data["assignment"]["requires_text_submission"] == course_assignment_content.assignment.requires_text_submission
    )
    assert (
        data["assignment"]["requires_file_submission"] == course_assignment_content.assignment.requires_file_submission
    )


def test_update_course_content_valid_quiz_data(superadmin_client, course_quiz_content):
    url = single_content_url(
        course_content_id=course_quiz_content.id,
        course_id=course_quiz_content.course.id,
        organization_id=course_quiz_content.course.organization.id,
    )
    payload = {
        "quiz": {
            "title": "Updated Quiz Title",
            "required_score": 80,
            "selection_strategy": "random",
            "deadline_days": 10,
            "limited_attempts": False,
            "is_blocking": False,
            "reminder_interval_days": 3,
            "questions": [
                {
                    "text": "What is Django?",
                    "priority": 1,
                    "answers": [
                        {"text": "A web framework", "is_correct": True},
                        {"text": "A type of dance", "is_correct": False},
                    ],
                }
            ],
        }
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_quiz_content.id
    assert data["quiz"]["title"] == "Updated Quiz Title"
    assert data["quiz"]["required_score"] == 80
    assert data["quiz"]["selection_strategy"] == "random"
    assert data["quiz"]["limited_attempts"] is False
    assert data["quiz"]["is_blocking"] is False
    assert data["quiz"]["deadline_days"] == 10
    assert len(data["quiz"]["questions"]) == 1
    assert data["quiz"]["questions"][0]["text"] == "What is Django?"
    assert len(data["quiz"]["questions"][0]["answers"]) == 2
    assert data["quiz"]["questions"][0]["answers"][0]["text"] == "A web framework"
    assert data["quiz"]["questions"][0]["answers"][0]["is_correct"] is True
    assert data["quiz"]["questions"][0]["answers"][1]["text"] == "A type of dance"
    assert data["quiz"]["questions"][0]["answers"][1]["is_correct"] is False
    assert data["quiz"]["reminder_interval_days"] == 3


def test_update_course_content_can_clear_quiz_reminder_interval(superadmin_client, course_quiz_content):
    course_quiz_content.quiz.reminder_interval_days = 3
    course_quiz_content.quiz.save()

    url = single_content_url(
        course_content_id=course_quiz_content.id,
        course_id=course_quiz_content.course.id,
        organization_id=course_quiz_content.course.organization.id,
    )
    payload = {"quiz": {"reminder_interval_days": None}}

    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    course_quiz_content.quiz.refresh_from_db()
    assert course_quiz_content.quiz.reminder_interval_days == 0
    assert response.json()["quiz"]["reminder_interval_days"] == 0


def test_update_course_content_waiting_period(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 3, "type": "days"}}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["waiting_period"] == {"period": 3, "type": "days"}


def test_update_course_content_limited_attempts(superadmin_client, course_quiz_content):
    url = single_content_url(
        course_content_id=course_quiz_content.id,
        course_id=course_quiz_content.course.id,
        organization_id=course_quiz_content.course.organization.id,
    )
    payload = {"quiz": {"limited_attempts": False}}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_quiz_content.id
    assert data["quiz"]["limited_attempts"] is False


def test_update_course_content_no_fields_provided(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        # No fields provided
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_viewer_cannot_update_course_content(viewer_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 3, "type": "days"}}
    response = viewer_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 403


def test_anonymous_user_cannot_update_course_content(anonymous_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 3, "type": "days"}}
    response = anonymous_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 401


@pytest.mark.parametrize("client", ["superadmin", "editor"], indirect=["client"])
def test_update_course_content_priority(client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"priority": 5}
    response = client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["priority"] == 5


def test_update_course_content_invalid_priority(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        "priority": -1  # Invalid priority
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_update_course_content_waiting_period_and_priority(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 4, "type": "hours"}, "priority": 3}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["waiting_period"] == {"period": 4, "type": "hours"}
    assert data["priority"] == 3


def test_update_course_content_with_valid_lesson_data(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"lesson": {"title": "Updated Lesson Title", "content": "Updated lesson content"}}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["lesson"]["title"] == "Updated Lesson Title"
    assert data["lesson"]["content"] == "Updated lesson content"


def test_update_course_content_with_valid_assignment_data(superadmin_client, course_assignment_content):
    url = single_content_url(
        course_content_id=course_assignment_content.id,
        course_id=course_assignment_content.course.id,
        organization_id=course_assignment_content.course.organization.id,
    )
    payload = {
        "assignment": {
            "title": "Updated Assignment Title",
            "description": "Updated assignment details",
            "deadline_days": 14,
            "requires_text_submission": False,
            "requires_file_submission": True,
        }
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_assignment_content.id
    assert data["type"] == "assignment"
    assert data["assignment"]["title"] == "Updated Assignment Title"
    assert data["assignment"]["description"] == "Updated assignment details"
    assert data["assignment"]["deadline_days"] == 14
    assert data["assignment"]["requires_text_submission"] is False
    assert data["assignment"]["requires_file_submission"] is True


def test_update_course_content_with_invalid_lesson_data(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        "lesson": {
            "title": 123,  # Invalid title type
            "content": "Updated content",
        }
    }
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_update_content_is_published(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"is_published": True}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["is_published"] is True

    payload = {"is_published": False}
    response = superadmin_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["is_published"] is False


# ---------------------------------------------------------------------------
# Cross-organization IDOR regression tests (GHSA-q8c3-pjqw-h7rw)
# ---------------------------------------------------------------------------


@pytest.fixture()
def other_org_course_content():
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        description="Belongs to a different organization.",
        organization=other_org,
    )
    lesson = Lesson.objects.create(title="Other Org Lesson", content="Secret content")
    return CourseContent.objects.create(
        course=other_course,
        priority=1,
        type=CourseContentType.LESSON,
        lesson=lesson,
        waiting_period=0,
    )


def test_list_course_content_cross_organization_returns_404(editor_client, other_org_course_content):
    url = reverse(
        "django_email_learning:api_platform:course_contents_list",
        kwargs={"organization_id": 1, "course_id": other_org_course_content.course_id},
    )
    response = editor_client.get(url)
    assert response.status_code == 404


def test_create_course_content_cross_organization_returns_404(editor_client, other_org_course_content):
    url = reverse(
        "django_email_learning:api_platform:course_contents_list",
        kwargs={"organization_id": 1, "course_id": other_org_course_content.course_id},
    )
    payload = {
        "content": {"title": "Injected", "content": "Injected content", "type": "lesson"},
        "priority": 1,
        "waiting_period": {"period": 1, "type": "days"},
    }
    response = editor_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 404


def test_get_single_course_content_cross_organization_returns_404(editor_client, other_org_course_content):
    url = single_content_url(
        course_content_id=other_org_course_content.id,
        course_id=other_org_course_content.course_id,
        organization_id=1,
    )
    response = editor_client.get(url)
    assert response.status_code == 404


def test_delete_single_course_content_cross_organization_returns_404(editor_client, other_org_course_content):
    url = single_content_url(
        course_content_id=other_org_course_content.id,
        course_id=other_org_course_content.course_id,
        organization_id=1,
    )
    response = editor_client.delete(url)
    assert response.status_code == 404
    assert CourseContent.objects.filter(id=other_org_course_content.id).exists()


def test_update_single_course_content_cross_organization_returns_404(editor_client, other_org_course_content):
    url = single_content_url(
        course_content_id=other_org_course_content.id,
        course_id=other_org_course_content.course_id,
        organization_id=1,
    )
    payload = {"lesson": {"title": "Hijacked", "content": "Hijacked content"}}
    response = editor_client.post(url, json.dumps(payload), content_type="application/json")
    assert response.status_code == 404
    other_org_course_content.lesson.refresh_from_db()
    assert other_org_course_content.lesson.title == "Other Org Lesson"
