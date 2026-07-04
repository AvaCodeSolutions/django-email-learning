import pytest
from django.urls import reverse

from django_email_learning.models import CourseContent, CourseContentType, Lesson


def get_url(course_id: int = 1) -> str:
    return reverse(
        "django_email_learning:platform:course_detail_view",
        kwargs={"course_id": course_id},
    )


def test_anonymous_user_redirects_to_login(anonymous_client):
    response = anonymous_client.get(get_url())
    assert response.status_code == 302
    assert "/login/" in response.url


@pytest.mark.parametrize(
    "client,role",
    [
        ("superadmin", "admin"),
        ("platform_admin", "admin"),
        ("editor", "editor"),
        ("viewer", "viewer"),
    ],
    indirect=["client"],
)
def test_authenticated_user_access_course_detail_view(client, role, course):
    response = client.get(get_url(course.id))
    assert response.status_code == 200
    assert response.context["appContext"]["userRole"] == role


def test_context_values(superadmin_client, course):
    response = superadmin_client.get(get_url(course.id))
    assert response.status_code == 200
    assert "apiBaseUrl" in response.context["appContext"]
    assert "platformBaseUrl" in response.context["appContext"]
    assert "activeOrganizationId" in response.context
    assert "userRole" in response.context["appContext"]
    assert response.context["appContext"]["isPlatformAdmin"] is True


def test_course_has_content_false_when_course_has_no_content(superadmin_client, course):
    response = superadmin_client.get(get_url(course.id))
    assert response.status_code == 200
    assert response.context["appContext"]["courseHasContent"] is False


def test_course_has_content_true_when_course_has_content(superadmin_client, course):
    lesson = Lesson.objects.create(title="Lesson", content="Content")
    CourseContent.objects.create(
        course=course,
        priority=1,
        type=CourseContentType.LESSON,
        lesson=lesson,
        waiting_period=0,
    )

    response = superadmin_client.get(get_url(course.id))

    assert response.status_code == 200
    assert response.context["appContext"]["courseHasContent"] is True
