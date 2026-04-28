from django.urls import reverse
from django_email_learning.services.jwt_service import generate_jwt
import pytest
from unittest import mock

URL = reverse("django_email_learning:api_jobs:deliver_contents")


def test_deliver_content_without_api_key(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 401
    assert response.json() == {"error": "Authorization header missing"}


@pytest.mark.parametrize("api_key", ["Basic valid_api_key", "without_space"])
def test_deliver_content_with_invalid_api_key(superadmin_client, api_key):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=api_key,
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": "Invalid Authorization header format. Expected: Bearer <API_KEY>"
    }


def test_deliver_content_with_invalid_decoded_api_key(superadmin_client):
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION="Bearer invalid_decoded_api_key",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid Json Web Token"}


def test_valid_jwt_format_but_invalid_api_key(superadmin_client):
    # This JWT is correctly formatted but does not correspond to any valid API key
    jwt = generate_jwt({"key": "invalid_key", "salt": "salt"})
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {jwt}",
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key"}


@mock.patch(
    "django_email_learning.jobs.deliver_contents_job.DeliverContentsJob.run",
    return_value=None,
)
def test_deliver_content_with_valid_api_key(mock_run, superadmin_client):
    create_key_response = superadmin_client.post(
        reverse("django_email_learning:api_platform:api_key_view")
    )
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )
    assert response.status_code == 202
    assert response.json() == {"status": "DeliverContentsJob triggered"}
    assert mock_run.called


@mock.patch(
    "django_email_learning.jobs.api.views.metric_service.job_execution_failed",
)
@mock.patch(
    "django_email_learning.jobs.deliver_contents_job.DeliverContentsJob.run",
    side_effect=Exception("boom"),
)
def test_deliver_content_failed_triggers_job_execution_failed_metric(
    mock_run, mock_job_execution_failed, superadmin_client
):
    create_key_response = superadmin_client.post(
        reverse("django_email_learning:api_platform:api_key_view")
    )
    response = superadmin_client.get(
        URL,
        HTTP_AUTHORIZATION=f"Bearer {create_key_response.json()['key']}",
    )

    assert response.status_code == 500
    assert response.json() == {"status": "DeliverContentsJob failed", "error": "boom"}
    mock_run.assert_called_once()
    mock_job_execution_failed.assert_called_once_with(job_name="deliver_contents")
