from django.urls import reverse

from django_email_learning.models import AssignmentSubmission, ContentDelivery
from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:api_personalised:assignment_submission")


def test_assignment_submission_api_valid_token(active_enrollment, course_assignment_content, anonymous_client):
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

    response = anonymous_client.post(
        URL,
        data={
            "token": token,
            "text_submission": "My assignment answer",
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "message" in response.json()

    submission = AssignmentSubmission.objects.get(delivery=content_delivery)
    assert submission.text_submission == "My assignment answer"


def test_assignment_submission_api_invalid_token(active_enrollment, course_assignment_content, anonymous_client):
    ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_assignment_content,
    )

    response = anonymous_client.post(
        URL,
        data={
            "token": "Invalid",
            "text_submission": "My assignment answer",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "The signature is invalid" in response.json()["error"]
