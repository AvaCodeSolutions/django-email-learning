from unittest import mock

from django.urls import reverse

from django_email_learning.models import JobExecution, JobName, JobStatus
from django_email_learning.services.jwt_service import generate_jwt

URL = reverse("django_email_learning:api_jobs:send_newsletters")


def test_send_newsletters_without_api_key(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


def test_send_newsletters_with_invalid_api_key(superadmin_client):
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION="Basic valid_api_key")
    assert response.status_code == 401


def test_send_newsletters_with_invalid_decoded_api_key(superadmin_client):
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION="Bearer invalid_decoded_api_key")
    assert response.status_code == 401


def test_send_newsletters_valid_jwt_format_but_invalid_api_key(superadmin_client):
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(URL, HTTP_AUTHORIZATION=f"Bearer {jwt}")
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


@mock.patch("django_email_learning.jobs.api.views.executor.submit")
def test_send_newsletters_with_valid_api_key(mock_submit, superadmin_client):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "SendNewslettersJob triggered"
    job_execution = JobExecution.objects.get(id=body["job_execution_id"])
    assert job_execution.job_name == JobName.SEND_NEWSLETTERS.value
    assert job_execution.status == JobStatus.RUNNING.value
    mock_submit.assert_called_once_with(
        job_name=JobName.SEND_NEWSLETTERS.value,
        job_execution_id=job_execution.id,
    )


def test_send_newsletters_already_running_returns_409(superadmin_client):
    running = JobExecution.objects.create(
        job_name=JobName.SEND_NEWSLETTERS.value,
        status=JobStatus.RUNNING.value,
    )
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 409
    assert response.json() == {
        "status": "SendNewslettersJob already running",
        "job_execution_id": running.id,
    }


@mock.patch("django_email_learning.jobs.api.views.metric_service.job_execution_failed")
@mock.patch("django_email_learning.jobs.api.views.executor.submit", side_effect=Exception("boom"))
def test_send_newsletters_submission_failure_triggers_job_execution_failed_metric(
    mock_submit, mock_job_execution_failed, superadmin_client
):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 500
    assert response.json() == {"status": "SendNewslettersJob failed", "error": "The request could not be completed."}
    # The exception text must not reach the client; it stays on job_execution.error.
    assert "boom" not in response.content.decode()
    mock_submit.assert_called_once()
    mock_job_execution_failed.assert_called_once_with(job_name=JobName.SEND_NEWSLETTERS.value)

    job_execution = JobExecution.objects.get(job_name=JobName.SEND_NEWSLETTERS.value)
    assert job_execution.status == JobStatus.FAILED.value
    assert job_execution.error == "boom"
