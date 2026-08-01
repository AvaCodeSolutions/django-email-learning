from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from django_email_learning.models import ContentDelivery
from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:api_personalised:file_upload")


def test_file_upload_valid_token(active_enrollment, course_assignment_content, anonymous_client):
    with override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}):
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

        uploaded_file = SimpleUploadedFile(
            "assignment.txt",
            b"my submission",
            content_type="text/plain",
        )

        response = anonymous_client.post(
            URL,
            data={"token": token, "file": uploaded_file},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["file_path"].startswith("uploads/")
        assert data["file_name"] == "assignment.txt"


def test_file_upload_invalid_token(anonymous_client):
    uploaded_file = SimpleUploadedFile(
        "assignment.txt",
        b"my submission",
        content_type="text/plain",
    )

    response = anonymous_client.post(
        URL,
        data={"token": "invalid", "file": uploaded_file},
    )

    assert response.status_code == 400
    assert "Invalid token" in response.json()["error"]
