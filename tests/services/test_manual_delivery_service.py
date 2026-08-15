from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

import django_email_learning.services.manual_delivery_service as manual_delivery_service_module
from django_email_learning.models import (
    ContentDelivery,
    CourseContent,
    DeliverySchedule,
    DeliveryStatus,
    Lesson,
)
from django_email_learning.services.manual_delivery_service import (
    ManualDeliveryOutcome,
    send_delivery_schedule_now,
)


@pytest.fixture
def scheduled_lesson_delivery(db, active_enrollment, course_lesson_content):
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    return DeliverySchedule.objects.create(
        delivery=delivery,
        time=timezone.now() + timedelta(days=2),
    )


def test_delivers_a_scheduled_delivery(scheduled_lesson_delivery):
    result = send_delivery_schedule_now(scheduled_lesson_delivery)

    assert result.outcome == ManualDeliveryOutcome.DELIVERED
    assert result.delivery_status == DeliveryStatus.DELIVERED


def test_does_not_claim_work_from_the_running_job(db, active_enrollment, course_lesson_content):
    """Constructing the job must not pull due schedules out of the queue.

    The database queue claims a batch the moment it is built, so a manual send
    that built one would mark unrelated due deliveries as PROCESSING and never
    process them.
    """
    other_delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    due_elsewhere = DeliverySchedule.objects.create(
        delivery=other_delivery,
        time=timezone.now() - timedelta(minutes=5),
    )
    target_delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=CourseContent.objects.create(
            course=course_lesson_content.course,
            priority=10,
            type="lesson",
            lesson=Lesson.objects.create(title="Second Lesson", content="Second lesson content"),
            waiting_period=3600,
            is_published=True,
        ),
    )
    target = DeliverySchedule.objects.create(delivery=target_delivery, time=timezone.now() + timedelta(days=1))

    send_delivery_schedule_now(target)

    due_elsewhere.refresh_from_db()
    assert due_elsewhere.status == DeliveryStatus.SCHEDULED


@pytest.mark.parametrize(
    "status",
    [DeliveryStatus.DELIVERED, DeliveryStatus.PROCESSING, DeliveryStatus.CANCELED, DeliveryStatus.BLOCKED],
)
def test_leaves_a_delivery_that_is_not_scheduled_alone(scheduled_lesson_delivery, status):
    scheduled_lesson_delivery.status = status
    scheduled_lesson_delivery.save()
    original_time = scheduled_lesson_delivery.time

    result = send_delivery_schedule_now(scheduled_lesson_delivery)

    assert result.outcome == ManualDeliveryOutcome.NOT_SCHEDULED
    assert result.delivery_status == status
    scheduled_lesson_delivery.refresh_from_db()
    assert scheduled_lesson_delivery.status == status
    assert scheduled_lesson_delivery.time == original_time


def test_blocks_the_delivery_when_processing_raises(scheduled_lesson_delivery):
    with (
        patch.object(
            manual_delivery_service_module.DeliverContentsJob,
            "process_delivery",
            side_effect=Exception("Simulated processing failure"),
        ),
        patch.object(manual_delivery_service_module.metric_service, "delivery_schedule_blocked"),
    ):
        result = send_delivery_schedule_now(scheduled_lesson_delivery)

    assert result.outcome == ManualDeliveryOutcome.FAILED
    assert result.delivery_status == DeliveryStatus.BLOCKED
    scheduled_lesson_delivery.refresh_from_db()
    assert scheduled_lesson_delivery.status == DeliveryStatus.BLOCKED


def test_returns_an_unsendable_delivery_to_scheduled(db, active_enrollment, course_assignment_content):
    """A content row with nothing to send must not be left PROCESSING.

    `process_delivery` recognises no content in that case and returns without
    touching the status, which would hide the schedule from the job forever.
    Model validation rejects an assignment content with no assignment, so the
    row is broken with a queryset update, the way a stray data change would.
    """
    course_assignment_content.is_published = True
    course_assignment_content.save()
    CourseContent.objects.filter(id=course_assignment_content.id).update(assignment=None)
    content_without_assignment = CourseContent.objects.get(id=course_assignment_content.id)
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=content_without_assignment,
    )
    schedule = DeliverySchedule.objects.create(delivery=delivery)

    with patch.object(manual_delivery_service_module.metric_service, "delivery_schedule_blocked") as blocked_metric:
        result = send_delivery_schedule_now(schedule)

    assert result.outcome == ManualDeliveryOutcome.FAILED
    assert result.delivery_status == DeliveryStatus.SCHEDULED
    schedule.refresh_from_db()
    assert schedule.status == DeliveryStatus.SCHEDULED
    blocked_metric.assert_called_once_with(content_without_assignment.id)


def test_cancels_a_delivery_whose_content_is_unpublished(db, active_enrollment, course_lesson_content):
    course_lesson_content.is_published = False
    course_lesson_content.save()
    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content=course_lesson_content,
    )
    schedule = DeliverySchedule.objects.create(delivery=delivery)

    result = send_delivery_schedule_now(schedule)

    assert result.outcome == ManualDeliveryOutcome.FAILED
    assert result.delivery_status == DeliveryStatus.CANCELED
