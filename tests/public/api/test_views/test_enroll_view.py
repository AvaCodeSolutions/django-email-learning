from django_email_learning.models import Enrollment
from django.urls import reverse
import pytest


URL = reverse("django_email_learning:api_public:enroll")


def test_enroll_view_creates_enrollment(anonymous_client, course):
    course.enabled = True
    course.save()
    enrollments_before = Enrollment.objects.filter(course=course).count()
    assert enrollments_before == 0

    payload = {
        "organization_id": course.organization_id,
        "email": "test@example.com",
        "course_slug": course.slug,
    }
    response = anonymous_client.post(URL, data=payload, content_type="application/json")
    assert response.status_code == 200
    assert Enrollment.objects.filter(
        learner__email="test@example.com", course=course
    ).exists()


@pytest.mark.parametrize(
    "payload",
    [
        {"organization_id": 1, "email": "invalid-email", "course_slug": "test-course"},
        {"organization_id": 1, "email": "test@example.com", "course_slug": ""},
        {
            "organization_id": None,
            "email": "test@example.com",
            "course_slug": "test-course",
        },
    ],
)
def test_enroll_view_invalid_payload(anonymous_client, payload):
    response = anonymous_client.post(URL, data=payload, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


def test_enroll_view_invalid_course_slug(anonymous_client, course):
    course.enabled = True
    course.save()

    payload = {
        "organization_id": course.organization_id,
        "email": "test@example.com",
        "course_slug": "non-existent-slug",
    }
    response = anonymous_client.post(URL, data=payload, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()
    assert "does not exist" in response.json()["error"]
