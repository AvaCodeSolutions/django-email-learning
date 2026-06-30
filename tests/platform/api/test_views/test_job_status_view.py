from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import JobName
from django_email_learning.platform.api.views import JobHealthStatus

URL = reverse("django_email_learning:api_platform:jobs_status")


def test_job_health_status_view(viewer_client, job_factory):
    # Create job executions now
    job_factory(name=JobName.DELIVER_CONTENTS)

    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.SUCCESS.value


def test_job_health_status_view_no_executions(viewer_client):
    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.CRITICAL.value


def test_job_health_status_view_execution_in_default_warning(viewer_client, job_factory):
    # Create a job execution with started_at more than 15 minutes ago but less than 45 minutes ago
    past_time = timezone.now() - timedelta(minutes=40)
    job_execution = job_factory(name=JobName.DELIVER_CONTENTS)
    job_execution.started_at = past_time
    job_execution.save()

    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.WARNING.value


def test_job_health_status_view_execution_in_critical(viewer_client, job_factory):
    # Create a job execution with started_at more than 45 minutes ago
    past_time = timezone.now() - timedelta(minutes=50)
    job_execution = job_factory(name=JobName.DELIVER_CONTENTS)
    job_execution.started_at = past_time
    job_execution.save()

    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.CRITICAL.value


def test_job_health_status_view_execution_in_success(viewer_client, job_factory):
    # Create a job execution with started_at less than 15 minutes ago
    past_time = timezone.now() - timedelta(minutes=10)
    job_execution = job_factory(name=JobName.DELIVER_CONTENTS)
    job_execution.started_at = past_time
    job_execution.save()

    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.SUCCESS.value


def test_job_health_status_view_configred_success_threshold(viewer_client, job_factory, settings):
    # Override settings for this test
    settings.DJANGO_EMAIL_LEARNING["JOB_HEALTH_SUCCESS_THRESHOLD_MINUTES"] = 20

    # Create a job execution with started_at more than 15 minutes ago but less than 20 minutes ago
    past_time = timezone.now() - timedelta(minutes=18)
    job_execution = job_factory(name=JobName.DELIVER_CONTENTS)
    job_execution.started_at = past_time
    job_execution.save()

    response = viewer_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert JobName.DELIVER_CONTENTS.value in data["jobs"]
    job_info = data["jobs"][JobName.DELIVER_CONTENTS.value]
    assert "job_health_status" in job_info
    assert job_info["job_health_status"] == JobHealthStatus.SUCCESS.value
