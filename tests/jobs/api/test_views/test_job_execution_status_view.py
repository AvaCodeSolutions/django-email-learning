from django.urls import reverse

from django_email_learning.models import JobExecution, JobName, JobStatus
from django_email_learning.services.jwt_service import generate_jwt


def _status_url(job_execution_id: int) -> str:
    return reverse(
        "django_email_learning:api_jobs:job_execution_status",
        kwargs={"job_execution_id": job_execution_id},
    )


def test_job_execution_status_without_api_key(superadmin_client):
    response = superadmin_client.get(_status_url(1))
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


def test_job_execution_status_valid_jwt_format_but_invalid_api_key(superadmin_client):
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(_status_url(1), HTTP_AUTHORIZATION=f"Bearer {jwt}")
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


def test_job_execution_status_returns_running_execution(superadmin_client):
    job_execution = JobExecution.objects.create(
        job_name=JobName.DELIVER_CONTENTS.value,
        status=JobStatus.RUNNING.value,
    )
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        _status_url(job_execution.id),
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_execution_id"] == job_execution.id
    assert body["job_name"] == JobName.DELIVER_CONTENTS.value
    assert body["status"] == JobStatus.RUNNING.value
    assert body["finished_at"] is None
    assert body["error"] is None


def test_job_execution_status_returns_failed_execution_with_error(superadmin_client):
    job_execution = JobExecution.objects.create(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.FAILED.value,
        error="boom",
    )
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        _status_url(job_execution.id),
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatus.FAILED.value
    assert body["error"] == "boom"


def test_job_execution_status_not_found(superadmin_client):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        _status_url(999999),
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 404
    assert response.json() == {"error": "Job execution not found"}
