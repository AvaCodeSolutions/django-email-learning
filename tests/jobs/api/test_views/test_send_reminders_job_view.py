from unittest import mock

import pytest
from django.urls import reverse

from django_email_learning.services.jwt_service import generate_jwt

URL = reverse("django_email_learning:api_jobs:send_quiz_reminders")


def test_send_reminders_without_api_key(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


@pytest.mark.parametrize("api_key", ["Basic valid_api_key", "without_space"])
def test_send_reminders_with_invalid_api_key(superadmin_client, api_key):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=api_key,
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid Authorization header format. Expected: Bearer <API_KEY>"}


def test_send_reminders_with_invalid_decoded_api_key(superadmin_client):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION="Bearer invalid_decoded_api_key",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid Json Web Token"}


def test_send_reminders_valid_jwt_format_but_invalid_api_key(superadmin_client):
    # This JWT is correctly formatted but does not correspond to any valid API key
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {jwt}",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


@mock.patch(
    "django_email_learning.jobs.send_reminders_job.SendRemindersJob.run",
    return_value=None,
)
def test_send_reminders_with_valid_api_key(mock_run, superadmin_client):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 202
    assert response.json() == {"status": "SendRemidersJob triggered"}
    assert mock_run.called


@mock.patch(
    "django_email_learning.jobs.api.views.metric_service.job_execution_failed",
)
@mock.patch(
    "django_email_learning.jobs.send_reminders_job.SendRemindersJob.run",
    side_effect=Exception("boom"),
)
def test_send_reminders_failed_triggers_job_execution_failed_metric(
    mock_run, mock_job_execution_failed, superadmin_client
):
    create_key_response = superadmin_client.post(reverse("django_email_learning:api_platform:api_keys_list"))
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 500
    assert response.json() == {"status": "SendRemidersJob failed", "error": "boom"}
    mock_run.assert_called_once()
    mock_job_execution_failed.assert_called_once_with(job_name="send_reminders")
