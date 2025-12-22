from django.urls import reverse
import pytest


def test_update_lesson_not_allowed_for_viewer(viewer_client, lesson):
    url = reverse(
        "django_email_learning:api:lesson_view",
        kwargs={"organization_id": 1, "lesson_id": lesson.id},
    )
    response = viewer_client.post(
        url,
        {"title": "Updated Lesson Title", "content": "Updated lesson content."},
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.parametrize("client", ["superadmin", "editor"], indirect=True)
def test_update_lesson_allowed_for_roles(client, lesson):
    url = reverse(
        "django_email_learning:api:lesson_view",
        kwargs={"organization_id": 1, "lesson_id": lesson.id},
    )
    response = client.post(
        url,
        {"title": "Updated Lesson Title", "content": "Updated lesson content."},
        content_type="application/json",
    )
    assert response.status_code == 204


def test_update_lesson_invalid_data(editor_client, lesson):
    url = reverse(
        "django_email_learning:api:lesson_view",
        kwargs={"organization_id": 1, "lesson_id": lesson.id},
    )
    response = editor_client.post(
        url,
        {"title": 2, "content": "Updated lesson content."},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_update_lesson_not_found(editor_client):
    url = reverse(
        "django_email_learning:api:lesson_view",
        kwargs={"organization_id": 1, "lesson_id": 9999},
    )
    response = editor_client.post(
        url,
        {"title": "Updated Lesson Title", "content": "Updated lesson content."},
        content_type="application/json",
    )
    assert response.status_code == 404
    assert response.json()["error"] == "Lesson not found"


def test_update_lesson_anonymous(anonymous_client, lesson):
    url = reverse(
        "django_email_learning:api:lesson_view",
        kwargs={"organization_id": 1, "lesson_id": lesson.id},
    )
    response = anonymous_client.post(
        url,
        {"title": "Updated Lesson Title", "content": "Updated lesson content."},
        content_type="application/json",
    )
    assert response.status_code == 401
