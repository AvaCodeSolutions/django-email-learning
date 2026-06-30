from django.urls import reverse

from django_email_learning.models import EnrollmentStatus


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


def test_enrollment_api_email_opened_event(viewer_client, content_delivery):
    from django.utils import timezone

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
