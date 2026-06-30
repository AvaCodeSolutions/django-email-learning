from datetime import timedelta

import pytest
from django.utils import timezone

from django_email_learning.models import DeliverySchedule, DeliveryStatus
from django_email_learning.services.defaults.database_delivery_queue import (
    DatabaseDeliveryQueue,
)


@pytest.fixture
def database_delivery_queue() -> DatabaseDeliveryQueue:
    queue = DatabaseDeliveryQueue()
    queue.ITERATOR_BATCH_SIZE = 2  # Set small batch size for testing
    return queue


def test_next_task_returns_none_when_no_tasks(db, database_delivery_queue):
    task = database_delivery_queue.next_task()
    assert task is None


def test_next_task_returns_scheduled_tasks(db, database_delivery_queue, content_delivery):
    # Create scheduled tasks
    task1 = DeliverySchedule.objects.create(
        delivery=content_delivery,
        status=DeliveryStatus.SCHEDULED,
        time=timezone.now() - timedelta(minutes=1),
    )
    task2 = DeliverySchedule.objects.create(
        delivery=content_delivery,
        status=DeliveryStatus.SCHEDULED,
        time=timezone.now() - timedelta(minutes=1),
    )
    task3 = DeliverySchedule.objects.create(
        delivery=content_delivery,
        status=DeliveryStatus.SCHEDULED,
        time=timezone.now() - timedelta(minutes=1),
    )

    # Fetch tasks using the delivery queue
    fetched_task1 = database_delivery_queue.next_task()
    fetched_task2 = database_delivery_queue.next_task()
    fetched_task3 = database_delivery_queue.next_task()
    fetched_task4 = database_delivery_queue.next_task()

    # Verify the fetched tasks
    assert fetched_task1 in [task1, task2, task3]
    assert fetched_task2 in [task1, task2, task3]
    assert fetched_task3 in [task1, task2, task3]
    assert fetched_task4 is None

    # Verify that the tasks' statuses have been updated to PROCESSING
    for task in [task1, task2, task3]:
        task.refresh_from_db()
        assert task.status == DeliveryStatus.PROCESSING
