from datetime import datetime

from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import CertificateField, EnrollmentStatus
from django_email_learning.services import jwt_service

NAME_ON_CERTIFICATE = "John Doe"

URL = reverse("django_email_learning:api_personalised:submit_certificate_form")


def test_submit_certificate_form_view_valid_token(enrollment, anonymous_client):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.save()

    token_payload = {
        "enrollment_id": enrollment.id,
    }
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    response = anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )
    assert response.status_code == 200

    enrollment.refresh_from_db()
    assert enrollment.certificate is not None
    cert = enrollment.certificate
    assert cert.name_on_certificate == NAME_ON_CERTIFICATE


def test_submit_certificate_form_strips_html_from_name(enrollment, anonymous_client):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.save()

    token_payload = {
        "enrollment_id": enrollment.id,
    }
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    response = anonymous_client.post(
        URL,
        data={"name": '<img src=x onerror="alert(document.cookie)">John Doe', "token": token},
        content_type="application/json",
    )
    assert response.status_code == 200

    enrollment.refresh_from_db()
    assert enrollment.certificate.name_on_certificate == "John Doe"


def test_submit_certificate_form_view_invalid_token(anonymous_client):
    token = "invalidtoken"
    response = anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid token" in response.json().get("error", "")


def test_submite_certificate_token_signed_by_different_secret(enrollment, anonymous_client):
    token_payload = {
        "enrollment_id": enrollment.id,
    }
    token = jwt_service.jwt.encode(
        token_payload,
        "some_different_secret_with_long_length",
        algorithm=jwt_service.ALGORITHM,
    )
    response = anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Invalid token" in response.json().get("error", "")


def test_submit_certificate_for_enrollment_in_an_invalid_state(enrollment, anonymous_client):
    token_payload = {
        "enrollment_id": enrollment.id,
    }
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    response = anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )
    assert response.status_code == 422
    assert "The enrollment is not completed. Certificate cannot be issued." in response.json().get("error", "")


def test_submit_certificate_form_snapshots_the_courses_certificate_fields(enrollment, anonymous_client):
    CertificateField.objects.create(course=enrollment.course, label="CPD Points", value="5", order=1)
    CertificateField.objects.create(course=enrollment.course, label="Level", value="Advanced", order=2)
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.save()

    token_payload = {"enrollment_id": enrollment.id}
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    response = anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )
    assert response.status_code == 200

    enrollment.refresh_from_db()
    assert enrollment.certificate.custom_fields == [
        {"label": "CPD Points", "value": "5"},
        {"label": "Level", "value": "Advanced"},
    ]


def test_issued_certificate_keeps_the_values_it_was_issued_with(enrollment, anonymous_client):
    field = CertificateField.objects.create(course=enrollment.course, label="CPD Points", value="5", order=1)
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.save()

    token_payload = {"enrollment_id": enrollment.id}
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )

    field.value = "10"
    field.save()
    CertificateField.objects.create(course=enrollment.course, label="Level", value="Advanced", order=2)

    enrollment.refresh_from_db()
    assert enrollment.certificate.custom_fields == [{"label": "CPD Points", "value": "5"}]


def test_submit_certificate_form_with_no_certificate_fields_stores_an_empty_list(enrollment, anonymous_client):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.save()

    token_payload = {"enrollment_id": enrollment.id}
    token = jwt_service.generate_jwt(token_payload, exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()))
    anonymous_client.post(
        URL,
        data={"name": NAME_ON_CERTIFICATE, "token": token},
        content_type="application/json",
    )

    enrollment.refresh_from_db()
    assert enrollment.certificate.custom_fields == []
