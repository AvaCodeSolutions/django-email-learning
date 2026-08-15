from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

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


def get_url(enrollment_id):
    return reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"enrollment_id": enrollment_id, "organization_id": 1},
    )


def test_enrollment_api_not_accessible_without_authentication(anonymous_client):
    url = get_url(enrollment_id=1)
    response = anonymous_client.get(url)
    assert response.status_code == 401


def test_enrollment_api_expected_payload(viewer_client, content_delivery):
    content_delivery.enrollment.status = EnrollmentStatus.ACTIVE
    content_delivery.enrollment.save()
    content_delivery.course_content.is_published = True
    content_delivery.course_content.save()
    content_delivery.delivery_schedules.first().status = "delivered"
    content_delivery.delivery_schedules.first().save()
    url = get_url(enrollment_id=content_delivery.enrollment.id)
    response = viewer_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == content_delivery.enrollment.id
    assert data["status"] == content_delivery.enrollment.status
    assert len(data["events"]) > 1
    content_sent_event_found = False
    for event in data["events"]:
        assert "type" in event
        assert "timestamp" in event
        if event["type"] == "content_sent":
            assert "event_data" in event
            content_sent_event_found = True
            assert event["event_data"]["course_content_id"] == content_delivery.course_content.id
            assert event["event_data"]["course_content_title"] == content_delivery.course_content.title
            assert event["event_data"]["course_content_type"] == content_delivery.course_content.type

    assert content_sent_event_found


def test_enrollment_api_cross_organization_returns_404(viewer_client):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        description="Belongs to a different organization.",
        organization=other_org,
    )
    other_learner = Learner.objects.create(email="other-org-learner@example.com", organization=other_org)
    other_enrollment = Enrollment.objects.create(learner=other_learner, course=other_course)

    response = viewer_client.get(get_url(enrollment_id=other_enrollment.id))
    assert response.status_code == 404


def test_enrollment_api_returns_the_next_scheduled_delivery(viewer_client, content_delivery, course_lesson_content):
    delivery = ContentDelivery.objects.create(
        enrollment=content_delivery.enrollment,
        course_content=course_lesson_content,
    )
    schedule = DeliverySchedule.objects.create(delivery=delivery, time=timezone.now() + timedelta(days=1))

    response = viewer_client.get(get_url(enrollment_id=content_delivery.enrollment.id))

    assert response.status_code == 200
    next_delivery = response.json()["next_delivery"]
    assert next_delivery["delivery_schedule_id"] == schedule.id
    assert next_delivery["course_content_id"] == course_lesson_content.id
    assert next_delivery["course_content_title"] == course_lesson_content.title
    assert next_delivery["course_content_type"] == course_lesson_content.type
    assert next_delivery["scheduled_at"] is not None


def test_enrollment_api_next_delivery_is_the_earliest_scheduled_one(
    viewer_client, content_delivery, course_lesson_content, course_assignment_content
):
    later = ContentDelivery.objects.create(
        enrollment=content_delivery.enrollment,
        course_content=course_assignment_content,
    )
    DeliverySchedule.objects.create(delivery=later, time=timezone.now() + timedelta(days=5))
    sooner = ContentDelivery.objects.create(
        enrollment=content_delivery.enrollment,
        course_content=course_lesson_content,
    )
    sooner_schedule = DeliverySchedule.objects.create(delivery=sooner, time=timezone.now() + timedelta(days=1))

    response = viewer_client.get(get_url(enrollment_id=content_delivery.enrollment.id))

    assert response.json()["next_delivery"]["delivery_schedule_id"] == sooner_schedule.id


def test_enrollment_api_next_delivery_is_null_without_a_scheduled_delivery(viewer_client, content_delivery):
    assert not content_delivery.delivery_schedules.filter(status=DeliveryStatus.SCHEDULED).exists()

    response = viewer_client.get(get_url(enrollment_id=content_delivery.enrollment.id))

    assert response.status_code == 200
    assert response.json()["next_delivery"] is None


def test_enrollment_api_email_opened_event(viewer_client, content_delivery):
    content_delivery.enrollment.status = EnrollmentStatus.ACTIVE
    content_delivery.enrollment.save()
    content_delivery.course_content.is_published = True
    content_delivery.course_content.save()
    schedule = content_delivery.delivery_schedules.first()
    schedule.status = "delivered"
    schedule.save()
    content_delivery.opened_at = timezone.now()
    content_delivery.save()

    url = get_url(enrollment_id=content_delivery.enrollment.id)
    response = viewer_client.get(url)
    assert response.status_code == 200
    data = response.json()
    email_opened_event = next((e for e in data["events"] if e["type"] == "email_opened"), None)
    assert email_opened_event is not None, f"email_opened event not found in {[e['type'] for e in data['events']]}"
    assert email_opened_event["event_data"]["course_content_id"] == content_delivery.course_content.id
