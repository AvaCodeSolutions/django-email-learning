from unittest import mock

import pytest
from django.urls import reverse

from django_email_learning.services.jwt_service import generate_jwt

URL = reverse("django_email_learning:api_jobs:cleanup_job_executions")


def test_cleanup_job_executions_without_api_key(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


@pytest.mark.parametrize("api_key", ["Basic valid_api_key", "without_space"])
def test_cleanup_job_executions_with_invalid_api_key(superadmin_client, api_key):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=api_key,
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": "Invalid Authorization header format. Expected: Bearer <API_KEY>"
    }


def test_cleanup_job_executions_with_invalid_decoded_api_key(superadmin_client):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION="Bearer invalid_decoded_api_key",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid Json Web Token"}


def test_cleanup_job_executions_valid_jwt_format_but_invalid_api_key(superadmin_client):
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {jwt}",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


@mock.patch(
    "django_email_learning.jobs.api.views.call_command",
    return_value=None,
)
def test_cleanup_job_executions_with_valid_api_key(
    mock_call_command, superadmin_client
):
    create_key_response = superadmin_client.post(
        reverse("django_email_learning:api_platform:api_key_view")
    )
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "CleanupJobExecutions command triggered",
        "output": "",
    }
    mock_call_command.assert_called_once()


@mock.patch(
    "django_email_learning.jobs.api.views.call_command",
    side_effect=Exception("boom"),
)
@mock.patch(
    "django_email_learning.jobs.api.views.metric_service.job_execution_failed",
)
def test_cleanup_job_executions_failed_triggers_job_execution_failed_metric(
    mock_job_execution_failed, mock_call_command, superadmin_client
):
    create_key_response = superadmin_client.post(
        reverse("django_email_learning:api_platform:api_key_view")
    )
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 500
    assert response.json() == {
        "status": "CleanupJobExecutions failed",
        "error": "boom",
    }
    mock_call_command.assert_called_once()
    mock_job_execution_failed.assert_called_once_with(job_name="cleanup_job_executions")


def test_cleanup_job_executions_returns_400_for_invalid_days(superadmin_client):
    create_key_response = superadmin_client.post(
        reverse("django_email_learning:api_platform:api_key_view")
    )
    response = superadmin_client.get(
        f"{URL}?days=invalid",
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "status": "CleanupJobExecutions failed",
        "error": "Invalid days",
    }
