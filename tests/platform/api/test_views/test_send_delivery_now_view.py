from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.jobs.deliver_contents_job import SendLessonCommand
from django_email_learning.models import (
    ContentDelivery,
    Course,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Organization,
)


def get_url(enrollment_id, delivery_schedule_id, organization_id=1):
    return reverse(
        "django_email_learning:api_platform:delivery_schedule_send_now",
        kwargs={
            "organization_id": organization_id,
            "enrollment_id": enrollment_id,
            "delivery_schedule_id": delivery_schedule_id,
        },
    )


@pytest.fixture
def scheduled_lesson_delivery(db, active_enrollment, course_lesson_content):
    """A lesson scheduled a day from now — the case "send now" exists for."""
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    return DeliverySchedule.objects.create(
        delivery=delivery,
        time=timezone.now() + timedelta(days=1),
    )


def test_send_now_requires_authentication(anonymous_client, scheduled_lesson_delivery):
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id)
    response = anonymous_client.post(url)
    assert response.status_code == 401


@pytest.mark.parametrize("client", ["viewer", "editor", "instructor"], indirect=True)
def test_send_now_is_forbidden_for_non_admins(client, scheduled_lesson_delivery):
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id)
    response = client.post(url)
    assert response.status_code == 403
    scheduled_lesson_delivery.refresh_from_db()
    assert scheduled_lesson_delivery.status == DeliveryStatus.SCHEDULED


@pytest.mark.parametrize("client", ["org_admin", "superadmin"], indirect=True)
def test_send_now_delivers_the_scheduled_content(client, scheduled_lesson_delivery):
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id)
    response = client.post(url)

    assert response.status_code == 200
    assert response.json()["status"] == DeliveryStatus.DELIVERED
    assert response.json()["delivery_schedule_id"] == scheduled_lesson_delivery.id

    scheduled_lesson_delivery.refresh_from_db()
    assert scheduled_lesson_delivery.status == DeliveryStatus.DELIVERED
    assert scheduled_lesson_delivery.delivered_at is not None
    # The schedule now says the delivery happened when it actually happened,
    # rather than keeping the future time it was originally due at.
    assert scheduled_lesson_delivery.time <= timezone.now()


def test_send_now_graduates_the_enrollment_after_the_last_content(org_admin_client, scheduled_lesson_delivery):
    """The follow-up work the job does must happen too, not just the email."""
    enrollment = scheduled_lesson_delivery.delivery.enrollment
    url = get_url(enrollment.id, scheduled_lesson_delivery.id)

    response = org_admin_client.post(url)

    assert response.status_code == 200
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.COMPLETED


def test_send_now_schedules_the_next_content(
    org_admin_client, scheduled_lesson_delivery, course_quiz_content, quiz_with_questions
):
    course_quiz_content.quiz = quiz_with_questions
    course_quiz_content.is_published = True
    course_quiz_content.save()
    enrollment = scheduled_lesson_delivery.delivery.enrollment
    url = get_url(enrollment.id, scheduled_lesson_delivery.id)

    response = org_admin_client.post(url)

    assert response.status_code == 200
    assert ContentDelivery.objects.filter(enrollment=enrollment, course_content=course_quiz_content).exists()
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE


def test_send_now_returns_409_when_the_delivery_is_not_scheduled(org_admin_client, scheduled_lesson_delivery):
    scheduled_lesson_delivery.status = DeliveryStatus.DELIVERED
    scheduled_lesson_delivery.save()
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id)

    response = org_admin_client.post(url)

    assert response.status_code == 409
    assert response.json()["delivery_status"] == DeliveryStatus.DELIVERED


def test_send_now_returns_500_when_sending_fails(org_admin_client, scheduled_lesson_delivery):
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id)

    with patch.object(SendLessonCommand, "execute", side_effect=Exception("Simulated sending failure")):
        response = org_admin_client.post(url)

    assert response.status_code == 500
    scheduled_lesson_delivery.refresh_from_db()
    # A failed attempt is rescheduled by the job's own retry logic, exactly as
    # it would be during a job run.
    assert scheduled_lesson_delivery.status == DeliveryStatus.SCHEDULED
    assert scheduled_lesson_delivery.failed_attempts == 1


def test_send_now_returns_404_for_unknown_delivery_schedule(org_admin_client, scheduled_lesson_delivery):
    url = get_url(scheduled_lesson_delivery.delivery.enrollment.id, scheduled_lesson_delivery.id + 1000)
    assert org_admin_client.post(url).status_code == 404


def test_send_now_returns_404_for_a_schedule_of_another_enrollment(org_admin_client, scheduled_lesson_delivery, course):
    other_learner = Learner.objects.create(email="other-learner@example.com", organization_id=1)
    other_enrollment = Enrollment.objects.create(learner=other_learner, course=course, status=EnrollmentStatus.ACTIVE)

    url = get_url(other_enrollment.id, scheduled_lesson_delivery.id)

    assert org_admin_client.post(url).status_code == 404
    scheduled_lesson_delivery.refresh_from_db()
    assert scheduled_lesson_delivery.status == DeliveryStatus.SCHEDULED


def test_send_now_returns_404_for_an_enrollment_of_another_organization(org_admin_client, course_lesson_content):
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
    delivery = ContentDelivery.objects.create(enrollment=other_enrollment, course_content=course_lesson_content)
    schedule = DeliverySchedule.objects.create(delivery=delivery)

    # Asked for under organization 1, which the admin does administer — the
    # enrollment belongs to organization 2, so it must not be reachable.
    assert org_admin_client.post(get_url(other_enrollment.id, schedule.id)).status_code == 404
    schedule.refresh_from_db()
    assert schedule.status == DeliveryStatus.SCHEDULED
