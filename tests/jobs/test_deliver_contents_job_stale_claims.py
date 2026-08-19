from datetime import timedelta

import pytest
from django.utils import timezone

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    DeliveryStatus,
    EnrollmentStatus,
    JobExecution,
    JobName,
    JobStatus,
)


@pytest.fixture
def due_schedule(db, enrollment, course_lesson_content):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()
    delivery = ContentDelivery.objects.create(enrollment=enrollment, course_content=course_lesson_content)
    return DeliverySchedule.objects.create(delivery=delivery, time=timezone.now() - timedelta(minutes=5))


def test_building_the_job_does_not_claim_due_schedules(due_schedule):
    """The queue must not claim work before `run()` decides to process it."""
    DeliverContentsJob()

    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.SCHEDULED
    assert due_schedule.claimed_at is None


def test_run_leaves_schedules_untouched_when_another_instance_is_running(due_schedule):
    """A run that exits on the lock must not strand rows in PROCESSING.

    The job used to claim a batch while being constructed, which happens before
    the run lock is checked. A second, overlapping run therefore marked up to a
    full batch as PROCESSING and then exited without processing any of it - and
    because the queue only looks for SCHEDULED rows, they were never seen again.
    """
    JobExecution.objects.create(job_name=JobName.DELIVER_CONTENTS.value, status=JobStatus.RUNNING.value)

    DeliverContentsJob().run()

    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.SCHEDULED
    assert due_schedule.claimed_at is None


def test_requeue_stale_claims_returns_abandoned_rows(due_schedule):
    due_schedule.status = DeliveryStatus.PROCESSING
    due_schedule.claimed_at = timezone.now() - timedelta(hours=3)
    due_schedule.save()

    requeued = DeliverContentsJob().requeue_stale_claims()

    assert requeued == 1
    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.SCHEDULED
    assert due_schedule.claimed_at is None


def test_requeue_stale_claims_returns_rows_claimed_before_the_field_existed(due_schedule):
    """Rows stuck by the original bug carry no `claimed_at`; nothing writes them."""
    DeliverySchedule.objects.filter(id=due_schedule.id).update(
        status=DeliveryStatus.PROCESSING,
        claimed_at=None,
    )

    assert DeliverContentsJob().requeue_stale_claims() == 1

    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.SCHEDULED


def test_requeue_stale_claims_leaves_in_flight_deliveries_alone(due_schedule):
    """A delivery being sent right now - e.g. by hand - must not be pulled back."""
    due_schedule.status = DeliveryStatus.PROCESSING
    due_schedule.claimed_at = timezone.now()
    due_schedule.save()

    assert DeliverContentsJob().requeue_stale_claims() == 0

    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.PROCESSING


def test_unhandled_content_type_is_blocked_not_left_processing(due_schedule):
    """`process_delivery` must never return leaving the row in PROCESSING."""
    due_schedule.status = DeliveryStatus.PROCESSING
    due_schedule.claimed_at = timezone.now()
    due_schedule.save()

    course_content = due_schedule.delivery.course_content
    course_content.type = "something_unknown"

    DeliverContentsJob().process_delivery(due_schedule)

    due_schedule.refresh_from_db()
    assert due_schedule.status == DeliveryStatus.BLOCKED
