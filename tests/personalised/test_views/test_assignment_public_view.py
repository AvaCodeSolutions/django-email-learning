from django.urls import reverse

from django_email_learning.models import ContentDelivery
from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:personalised:assignment_public_view")


def test_assignment_public_view_valid_token(active_enrollment, course_assignment_content, anonymous_client):
    course_assignment_content.is_published = True
    course_assignment_content.save()

    content_delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_assignment_content,
    )

    token = jwt_service.generate_jwt(
        {
            "delivery_id": content_delivery.id,
            "delivery_hash": content_delivery.hash_value,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}")

    assert response.status_code == 200
    assert "assignment" in response.context["appContext"]

    assignment = response.context["appContext"]["assignment"]
    assert assignment["id"] == content_delivery.course_content.assignment.id


def test_assignment_public_view_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")

    assert response.status_code == 400
    assert "The link is not valid" in response.content.decode()
