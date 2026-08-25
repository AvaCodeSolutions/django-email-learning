from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import (
    ContentDelivery,
    Course,
    DeactivationReason,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Organization,
)


def get_url(enrollment_id, organization_id=1):
    return reverse(
        "django_email_learning:api_platform:enrollment_cancel",
        kwargs={
            "organization_id": organization_id,
            "enrollment_id": enrollment_id,
        },
    )


@pytest.fixture
def enrollment_with_scheduled_delivery(db, active_enrollment, course_lesson_content):
    """An active enrollment with a lesson still waiting to go out."""
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    DeliverySchedule.objects.create(
        delivery=delivery,
        time=timezone.now() + timedelta(days=1),
    )
    return active_enrollment


def test_cancel_requires_authentication(anonymous_client, active_enrollment):
    response = anonymous_client.post(get_url(active_enrollment.id))

    assert response.status_code == 401
    active_enrollment.refresh_from_db()
    assert active_enrollment.status == EnrollmentStatus.ACTIVE


@pytest.mark.parametrize("client", ["viewer", "editor", "instructor"], indirect=True)
def test_cancel_is_forbidden_for_non_admins(client, active_enrollment):
    response = client.post(get_url(active_enrollment.id))

    assert response.status_code == 403
    active_enrollment.refresh_from_db()
    assert active_enrollment.status == EnrollmentStatus.ACTIVE


@pytest.mark.parametrize("client", ["org_admin", "superadmin"], indirect=True)
def test_cancel_deactivates_the_enrollment_as_revoked(client, active_enrollment):
    response = client.post(get_url(active_enrollment.id))

    assert response.status_code == 200
    assert response.json() == {
        "id": active_enrollment.id,
        "status": EnrollmentStatus.DEACTIVATED,
        "deactivation_reason": DeactivationReason.REVOKED,
    }

    active_enrollment.refresh_from_db()
    assert active_enrollment.status == EnrollmentStatus.DEACTIVATED
    # Not CANCELED: that reason means the learner unsubscribed themselves.
    assert active_enrollment.deactivation_reason == DeactivationReason.REVOKED
    assert active_enrollment.final_state_at is not None


def test_cancel_cancels_pending_deliveries(org_admin_client, enrollment_with_scheduled_delivery):
    """The point of cancelling: nothing further reaches the learner's inbox."""
    response = org_admin_client.post(get_url(enrollment_with_scheduled_delivery.id))

    assert response.status_code == 200
    schedules = DeliverySchedule.objects.filter(delivery__enrollment=enrollment_with_scheduled_delivery)
    assert [schedule.status for schedule in schedules] == [DeliveryStatus.CANCELED]


def test_cancel_leaves_a_delivery_in_flight_alone(org_admin_client, enrollment_with_scheduled_delivery):
    """A claimed schedule belongs to the job (or a manual send) — that email is
    going out either way, and taking the row back would strand it."""
    schedule = DeliverySchedule.objects.get(delivery__enrollment=enrollment_with_scheduled_delivery)
    schedule.status = DeliveryStatus.PROCESSING
    schedule.claimed_at = timezone.now()
    schedule.save()

    response = org_admin_client.post(get_url(enrollment_with_scheduled_delivery.id))

    assert response.status_code == 200
    schedule.refresh_from_db()
    assert schedule.status == DeliveryStatus.PROCESSING


def test_cancel_works_for_an_unverified_enrollment(org_admin_client, enrollment):
    assert enrollment.status == EnrollmentStatus.UNVERIFIED

    response = org_admin_client.post(get_url(enrollment.id))

    assert response.status_code == 200
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DEACTIVATED
    assert enrollment.deactivation_reason == DeactivationReason.REVOKED


def test_cancel_records_the_deactivation_metric(org_admin_client, active_enrollment):
    with patch(
        "django_email_learning.services.enrollment_cancellation_service.metric_service"
    ) as mocked_metric_service:
        org_admin_client.post(get_url(active_enrollment.id))

    mocked_metric_service.user_enrollment_deactivated.assert_called_once_with(
        course_slug=active_enrollment.course.slug,
        organization_id=active_enrollment.course.organization_id,
        reason=DeactivationReason.REVOKED.value,
    )


def test_cancel_shows_in_the_enrollment_timeline(org_admin_client, active_enrollment):
    """The admin's next look at the enrollment has to explain what happened."""
    org_admin_client.post(get_url(active_enrollment.id))

    detail_url = reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": 1, "enrollment_id": active_enrollment.id},
    )
    events = org_admin_client.get(detail_url).json()["events"]

    deactivated_events = [event for event in events if event["type"] == "deactivated"]
    assert len(deactivated_events) == 1
    assert deactivated_events[0]["event_data"]["reason"] == DeactivationReason.REVOKED


def test_cancel_returns_409_for_a_completed_enrollment(org_admin_client, active_enrollment):
    active_enrollment.status = EnrollmentStatus.COMPLETED
    active_enrollment.save()

    response = org_admin_client.post(get_url(active_enrollment.id))

    assert response.status_code == 409
    assert response.json()["status"] == EnrollmentStatus.COMPLETED
    active_enrollment.refresh_from_db()
    assert active_enrollment.status == EnrollmentStatus.COMPLETED


def test_cancel_returns_409_for_an_already_deactivated_enrollment(org_admin_client, active_enrollment):
    active_enrollment.status = EnrollmentStatus.DEACTIVATED
    active_enrollment.deactivation_reason = DeactivationReason.CANCELED
    active_enrollment.save()

    response = org_admin_client.post(get_url(active_enrollment.id))

    assert response.status_code == 409
    active_enrollment.refresh_from_db()
    # The original reason survives — an admin cancelling afterwards must not
    # rewrite the record of the learner having unsubscribed.
    assert active_enrollment.deactivation_reason == DeactivationReason.CANCELED


def test_cancel_returns_404_for_an_unknown_enrollment(org_admin_client, active_enrollment):
    assert org_admin_client.post(get_url(active_enrollment.id + 1000)).status_code == 404


def test_cancel_returns_404_for_an_enrollment_of_another_organization(org_admin_client, db):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        organization=other_org,
    )
    other_learner = Learner.objects.create(email="other-org-learner@example.com", organization=other_org)
    other_enrollment = Enrollment.objects.create(
        learner=other_learner, course=other_course, status=EnrollmentStatus.ACTIVE
    )

    # Asked for under organization 1, which the admin does administer — the
    # enrollment belongs to organization 2, so it must not be reachable.
    assert org_admin_client.post(get_url(other_enrollment.id)).status_code == 404
    other_enrollment.refresh_from_db()
    assert other_enrollment.status == EnrollmentStatus.ACTIVE


def test_cancel_allows_re_enrolling_the_learner_afterwards(org_admin_client, active_enrollment):
    """`unique_active_enrollment` only covers non-deactivated rows, so a
    cancelled learner can be enrolled in the same course again."""
    org_admin_client.post(get_url(active_enrollment.id))

    new_enrollment = Enrollment.objects.create(
        learner=active_enrollment.learner,
        course=active_enrollment.course,
    )

    assert new_enrollment.id is not None
