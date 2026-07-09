from unittest import mock

from django.urls import reverse

from django_email_learning.services.jwt_service import generate_jwt

URL = reverse("django_email_learning:api_jobs:send_certificate_pdfs")


def test_send_certificate_pdfs_without_api_key(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


def test_send_certificate_pdfs_with_invalid_api_key(superadmin_client):
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION="Basic valid_api_key")
    assert response.status_code == 401


def test_send_certificate_pdfs_with_invalid_decoded_api_key(superadmin_client):
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION="Bearer invalid_decoded_api_key")
    assert response.status_code == 401


def test_send_certificate_pdfs_valid_jwt_format_but_invalid_api_key(superadmin_client):
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {jwt}")
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


@mock.patch(
    "django_email_learning.jobs.send_certificate_pdfs_job.SendCertificatePdfsJob.run",
    return_value=None,
)
def test_send_certificate_pdfs_with_valid_api_key(mock_run, superadmin_client):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 202
    assert response.json() == {"status": "SendCertificatePdfsJob triggered"}
    assert mock_run.called


@mock.patch(
    "django_email_learning.jobs.api.views.metric_service.job_execution_failed",
)
@mock.patch(
    "django_email_learning.jobs.send_certificate_pdfs_job.SendCertificatePdfsJob.run",
    side_effect=Exception("boom"),
)
def test_send_certificate_pdfs_failed_triggers_job_execution_failed_metric(
    mock_run, mock_job_execution_failed, superadmin_client
):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 500
    assert response.json() == {"status": "SendCertificatePdfsJob failed", "error": "boom"}
    mock_run.assert_called_once()
    mock_job_execution_failed.assert_called_once_with(job_name="send_certificate_pdfs")
