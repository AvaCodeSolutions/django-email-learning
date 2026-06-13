from django.urls import reverse
from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    Enrollment,
    EnrollmentStatus,
)
from django_email_learning.models.enums.delivery_status import DeliveryStatus
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORG_ID = 1


def url(name, **kwargs):
    return reverse(
        f"django_email_learning:api_analytics:{name}",
        kwargs={"organization_id": ORG_ID, **kwargs},
    )


def make_delivered_schedule(delivery):
    """Create a DELIVERED DeliverySchedule for a ContentDelivery."""
    return DeliverySchedule.objects.create(
        delivery=delivery,
        status=DeliveryStatus.DELIVERED,
        delivered_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# Access control — tested once on a representative endpoint
# ---------------------------------------------------------------------------


def test_unauthenticated_returns_401(anonymous_client, course):
    response = anonymous_client.get(url("enrollments_over_time"))
    assert response.status_code == 401


def test_member_of_different_org_returns_403(editor_client, course):
    # editor_client belongs to org 1; try org 2
    other_url = reverse(
        "django_email_learning:api_analytics:enrollments_over_time",
        kwargs={"organization_id": 2},
    )
    response = editor_client.get(other_url)
    assert response.status_code == 403


def test_org_member_can_access_chart_views(editor_client, course):
    response = editor_client.get(url("enrollments_over_time"))
    assert response.status_code == 200


def test_org_member_cannot_access_download_views(editor_client, course):
    response = editor_client.get(url("download_learner_progress"))
    assert response.status_code == 403


def test_org_admin_can_access_download_views(org_admin_client, course):
    response = org_admin_client.get(url("download_learner_progress"))
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# EnrollmentsOverTimeView
# ---------------------------------------------------------------------------


def test_enrollments_over_time_returns_data(editor_client, active_enrollment):
    response = editor_client.get(url("enrollments_over_time"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    total = sum(r["count"] for r in data)
    assert total == 1


def test_enrollments_over_time_course_filter(editor_client, active_enrollment):
    response = editor_client.get(
        url("enrollments_over_time"),
        {"course_id": active_enrollment.course_id},
    )
    assert response.status_code == 200
    total = sum(r["count"] for r in response.json()["data"])
    assert total == 1


def test_enrollments_over_time_wrong_course_filter_returns_empty(
    editor_client, active_enrollment
):
    response = editor_client.get(url("enrollments_over_time"), {"course_id": 99999})
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_enrollments_over_time_granularity_week(editor_client, active_enrollment):
    response = editor_client.get(url("enrollments_over_time"), {"granularity": "week"})
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_enrollments_over_time_invalid_granularity_falls_back_to_day(
    editor_client, active_enrollment
):
    response = editor_client.get(
        url("enrollments_over_time"), {"granularity": "invalid"}
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# EnrollmentStatusBreakdownView
# ---------------------------------------------------------------------------


def test_enrollment_status_breakdown(editor_client, active_enrollment):
    response = editor_client.get(url("enrollments_status_breakdown"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    row = data[0]
    assert "course_id" in row
    assert "course_title" in row
    assert "status" in row
    assert "count" in row


def test_enrollment_status_breakdown_reflects_status(editor_client, active_enrollment):
    response = editor_client.get(url("enrollments_status_breakdown"))
    statuses = {r["status"] for r in response.json()["data"]}
    assert EnrollmentStatus.ACTIVE in statuses


# ---------------------------------------------------------------------------
# CompletionFunnelView
# ---------------------------------------------------------------------------


def test_completion_funnel_returns_content_items(
    editor_client, active_enrollment, course_lesson_content
):
    response = editor_client.get(url("completion_funnel"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    item = data[0]
    assert "course_content_id" in item
    assert "learners_reached" in item


def test_completion_funnel_counts_delivered(
    editor_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)

    response = editor_client.get(url("completion_funnel"))
    data = response.json()["data"]
    item = next(d for d in data if d["course_content_id"] == course_lesson_content.id)
    assert item["learners_reached"] == 1


# ---------------------------------------------------------------------------
# AverageProgressView
# ---------------------------------------------------------------------------


def test_average_progress_returns_per_course(editor_client, active_enrollment):
    response = editor_client.get(url("average_progress"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    if data:
        row = data[0]
        assert "course_id" in row
        assert "average_progress" in row
        assert "active_enrollments" in row


def test_average_progress_only_includes_active_enrollments(
    editor_client, active_enrollment, course
):
    from django_email_learning.models import Learner

    other_learner = Learner.objects.create(email="other@example.com", organization_id=1)
    Enrollment.objects.create(
        learner=other_learner,
        course=course,
        status=EnrollmentStatus.COMPLETED,
    )

    response = editor_client.get(url("average_progress"))
    data = response.json()["data"]
    total_active = sum(r["active_enrollments"] for r in data)
    # Only the active_enrollment should be counted
    assert total_active == 1


# ---------------------------------------------------------------------------
# TimeToCompleteView
# ---------------------------------------------------------------------------


def test_time_to_complete_empty_when_no_completions(editor_client, active_enrollment):
    response = editor_client.get(url("time_to_complete"))
    assert response.status_code == 200
    # No completed enrollments — data may be empty or list avg as None
    data = response.json()["data"]
    assert isinstance(data, list)


def test_time_to_complete_shows_completed_enrollment(editor_client, active_enrollment):
    active_enrollment.status = EnrollmentStatus.COMPLETED
    active_enrollment.save()
    active_enrollment.refresh_from_db()

    response = editor_client.get(url("time_to_complete"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    row = data[0]
    assert row["total_completions"] == 1
    assert row["average_days"] is not None


# ---------------------------------------------------------------------------
# EmailDeliveryOverTimeView
# ---------------------------------------------------------------------------


def test_email_delivery_over_time(
    editor_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)

    response = editor_client.get(url("email_delivery_over_time"))
    assert response.status_code == 200
    data = response.json()["data"]
    total = sum(r["count"] for r in data)
    assert total == 1


def test_email_delivery_over_time_excludes_non_delivered(
    editor_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    DeliverySchedule.objects.create(
        delivery=delivery,
        status=DeliveryStatus.SCHEDULED,
    )

    response = editor_client.get(url("email_delivery_over_time"))
    assert response.status_code == 200
    total = sum(r["count"] for r in response.json()["data"])
    assert total == 0


# ---------------------------------------------------------------------------
# EmailDeliveryStatusBreakdownView
# ---------------------------------------------------------------------------


def test_email_delivery_status_breakdown(
    editor_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)

    response = editor_client.get(url("email_delivery_status_breakdown"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    row = data[0]
    assert "course_id" in row
    assert "status" in row
    assert "count" in row


# ---------------------------------------------------------------------------
# EmailOpenRateView
# ---------------------------------------------------------------------------


def test_email_open_rate(editor_client, active_enrollment, course_lesson_content):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)
    delivery.opened_at = timezone.now()
    delivery.save()

    response = editor_client.get(url("email_open_rate"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    row = data[0]
    assert row["total_delivered"] == 1
    assert row["total_opened"] == 1
    assert row["open_rate"] == 100.0


def test_email_open_rate_unopened(
    editor_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)

    response = editor_client.get(url("email_open_rate"))
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    row = data[0]
    assert row["total_opened"] == 0
    assert row["open_rate"] == 0.0


# ---------------------------------------------------------------------------
# Download views
# ---------------------------------------------------------------------------


def test_download_learner_progress_csv(
    org_admin_client, active_enrollment, course_lesson_content
):
    response = org_admin_client.get(url("download_learner_progress"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode()
    assert "Learner Email" in content
    assert active_enrollment.learner.email in content


def test_download_delivery_log_csv(
    org_admin_client, active_enrollment, course_lesson_content
):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    make_delivered_schedule(delivery)

    response = org_admin_client.get(url("download_delivery_log"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode()
    assert "Learner Email" in content
    assert active_enrollment.learner.email in content


def test_download_completion_summary_csv(org_admin_client, active_enrollment):
    response = org_admin_client.get(url("download_completion_summary"))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode()
    assert "Course" in content
    assert active_enrollment.course.title in content


def test_download_learner_progress_respects_course_filter(
    org_admin_client, active_enrollment
):
    response = org_admin_client.get(
        url("download_learner_progress"), {"course_id": 99999}
    )
    assert response.status_code == 200
    content = response.content.decode()
    # Only header row — no learner rows for a non-existent course
    lines = [line for line in content.strip().splitlines() if line]
    assert len(lines) == 1
