import pytest

from django.urls import reverse
import json

LESSON_TITLE = "Introduction to Python"
LESSON_CONTENT = "Welcome to the Python course!"


def get_url() -> str:
    return reverse(
        "django_email_learning:api:course_content_view",
        kwargs={"organization_id": 1, "course_id": 1},
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
    }


@pytest.fixture()
def create_course(superadmin_client):
    url = reverse(
        "django_email_learning:api:course_view",
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
    assert data["lesson"]["is_published"] is False
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
    assert data["quiz"]["is_published"] is False
    assert data["priority"] == 2
    assert data["waiting_period"] == {"period": 1, "type": "hours"}
    assert data["quiz"]["title"] == "Quiz 1"
    assert data["quiz"]["required_score"] == 70
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
