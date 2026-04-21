import pytest

from django.urls import reverse
import json


LESSON_TITLE = "Introduction to Python"
LESSON_CONTENT = "Welcome to the Python course!"


def get_url() -> str:
    return reverse(
        "django_email_learning:api_platform:course_content_view",
        kwargs={"organization_id": 1, "course_id": 1},
    )


def single_content_url(
    course_content_id: int, course_id: int, organization_id: int = 1
) -> str:
    return reverse(
        "django_email_learning:api_platform:single_course_content_view",
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
        "django_email_learning:api_platform:course_view",
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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


@pytest.mark.parametrize(
    "title,content", [(None, LESSON_CONTENT), (LESSON_TITLE, None)]
)
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

    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = viewer_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = anonymous_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response1 = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response1.status_code == 201

    response2 = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.parametrize(
    "client", ["superadmin", "editor", "viewer"], indirect=["client"]
)
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
    superadmin_client.post(
        url, json.dumps(lesson_payload), content_type="application/json"
    )

    # Create a quiz content
    quiz_payload = {
        "content": {
            "type": "quiz",
            "title": "Quiz 1",
            "required_score": 70,
            "selection_strategy": "random",
            "deadline_days": 14,
            "is_blocking": False,
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
    superadmin_client.post(
        url, json.dumps(quiz_payload), content_type="application/json"
    )

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
    response = superadmin_client.post(
        url, json.dumps(lesson_payload), content_type="application/json"
    )
    assert response.status_code == 201
    data = response.json()
    course_content_id = data["id"]

    # Delete the created course content
    delete_url = reverse(
        "django_email_learning:api_platform:single_course_content_view",
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


def test_viewer_cannot_delete_course_content(viewer_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    response = viewer_client.delete(url)
    assert response.status_code == 403


def test_anonymous_user_cannot_delete_course_content(
    anonymous_client, course_lesson_content
):
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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


def test_update_course_content_waiting_period(superadmin_client, course_lesson_content):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 3, "type": "days"}}
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_quiz_content.id
    assert data["quiz"]["limited_attempts"] is False


def test_update_course_content_no_fields_provided(
    superadmin_client, course_lesson_content
):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        # No fields provided
    }
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = viewer_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 403


def test_anonymous_user_cannot_update_course_content(
    anonymous_client, course_lesson_content
):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 3, "type": "days"}}
    response = anonymous_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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


def test_update_course_content_invalid_priority(
    superadmin_client, course_lesson_content
):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        "priority": -1  # Invalid priority
    }
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_update_course_content_waiting_period_and_priority(
    superadmin_client, course_lesson_content
):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {"waiting_period": {"period": 4, "type": "hours"}, "priority": 3}
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["waiting_period"] == {"period": 4, "type": "hours"}
    assert data["priority"] == 3


def test_update_course_content_with_valid_lesson_data(
    superadmin_client, course_lesson_content
):
    url = single_content_url(
        course_content_id=course_lesson_content.id,
        course_id=course_lesson_content.course.id,
        organization_id=course_lesson_content.course.organization.id,
    )
    payload = {
        "lesson": {"title": "Updated Lesson Title", "content": "Updated lesson content"}
    }
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["lesson"]["title"] == "Updated Lesson Title"
    assert data["lesson"]["content"] == "Updated lesson content"


def test_update_course_content_with_invalid_lesson_data(
    superadmin_client, course_lesson_content
):
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
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
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["is_published"] is True

    payload = {"is_published": False}
    response = superadmin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_lesson_content.id
    assert data["is_published"] is False
