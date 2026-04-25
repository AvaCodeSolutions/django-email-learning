from datetime import timedelta

import pytest
from django.utils import timezone

from django_email_learning.models import (
    ContentDelivery,
    CourseContent,
    DeliverySchedule,
    DeliveryStatus,
    Quiz,
)
from django_email_learning.services.defaults.database_reminder_queue import (
    DatabaseReminderQueue,
)


@pytest.fixture
def database_reminder_queue() -> DatabaseReminderQueue:
    queue = DatabaseReminderQueue()
    queue.ITERATOR_BATCH_SIZE = 2
    return queue


def test_next_task_returns_none_when_no_tasks(db, database_reminder_queue):
    task = database_reminder_queue.next_task()
    assert task is None


def test_next_task_returns_only_ready_reminder_tasks_and_sets_processing_state(
    db, database_reminder_queue, enrollment, course_quiz_content, course, quiz
):
    enrollment.status = "active"
    enrollment.save()

    ready_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    ContentDelivery.objects.filter(id=ready_delivery.id).update(
        remind_at=timezone.now() - timedelta(minutes=1),
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    DeliverySchedule.objects.create(
        delivery=ready_delivery,
        status=DeliveryStatus.DELIVERED,
        time=timezone.now() - timedelta(hours=1),
    )

    not_ready_quiz = Quiz.objects.create(
        title="Not Ready Quiz",
        required_score=70,
        selection_strategy="random",
        deadline_days=14,
    )
    not_ready_content = CourseContent.objects.create(
        course=course,
        priority=10,
        type="quiz",
        quiz=not_ready_quiz,
        waiting_period=3600,
    )
    not_ready_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=not_ready_content,
    )
    ContentDelivery.objects.filter(id=not_ready_delivery.id).update(
        remind_at=timezone.now() + timedelta(minutes=5),
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    DeliverySchedule.objects.create(
        delivery=not_ready_delivery,
        status=DeliveryStatus.DELIVERED,
    )

    already_processed_quiz = Quiz.objects.create(
        title="Already Processed Quiz",
        required_score=70,
        selection_strategy="random",
        deadline_days=14,
    )
    already_processed_content = CourseContent.objects.create(
        course=course,
        priority=11,
        type="quiz",
        quiz=already_processed_quiz,
        waiting_period=3600,
    )
    already_processed_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=already_processed_content,
    )
    ContentDelivery.objects.filter(id=already_processed_delivery.id).update(
        remind_at=timezone.now() - timedelta(minutes=1),
        reminder_state=ContentDelivery.ReminderStatus.PROCESSING,
    )
    DeliverySchedule.objects.create(
        delivery=already_processed_delivery,
        status=DeliveryStatus.DELIVERED,
    )

    fetched_task = database_reminder_queue.next_task()
    no_more_tasks = database_reminder_queue.next_task()

    assert fetched_task is not None
    assert fetched_task.delivery_id == ready_delivery.id
    assert no_more_tasks is None

    ready_delivery.refresh_from_db()
    not_ready_delivery.refresh_from_db()
    already_processed_delivery.refresh_from_db()

    assert ready_delivery.reminder_state == ContentDelivery.ReminderStatus.PROCESSING
    assert not_ready_delivery.reminder_state == ContentDelivery.ReminderStatus.PENDING
    assert (
        already_processed_delivery.reminder_state
        == ContentDelivery.ReminderStatus.PROCESSING
    )


def test_next_task_returns_latest_schedule_for_each_delivery(
    db, database_reminder_queue, enrollment, course_quiz_content, course, quiz
):
    enrollment.status = "active"
    enrollment.save()

    second_quiz = Quiz.objects.create(
        title="Second Quiz",
        required_score=70,
        selection_strategy="random",
        deadline_days=14,
    )
    second_content = CourseContent.objects.create(
        course=course, priority=10, type="quiz", quiz=second_quiz, waiting_period=3600
    )

    first_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    second_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=second_content,
    )

    ContentDelivery.objects.filter(
        id__in=[first_delivery.id, second_delivery.id]
    ).update(
        remind_at=timezone.now() - timedelta(minutes=1),
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )

    first_old_schedule = DeliverySchedule.objects.create(
        delivery=first_delivery,
        status=DeliveryStatus.DELIVERED,
        time=timezone.now() - timedelta(hours=2),
    )
    first_latest_schedule = DeliverySchedule.objects.create(
        delivery=first_delivery,
        status=DeliveryStatus.DELIVERED,
        time=timezone.now() - timedelta(hours=1),
    )
    second_old_schedule = DeliverySchedule.objects.create(
        delivery=second_delivery,
        status=DeliveryStatus.DELIVERED,
        time=timezone.now() - timedelta(hours=3),
    )
    second_latest_schedule = DeliverySchedule.objects.create(
        delivery=second_delivery,
        status=DeliveryStatus.DELIVERED,
        time=timezone.now() - timedelta(minutes=30),
    )

    fetched_1 = database_reminder_queue.next_task()
    fetched_2 = database_reminder_queue.next_task()
    fetched_3 = database_reminder_queue.next_task()

    fetched_ids = {fetched_1.id, fetched_2.id}

    assert first_old_schedule.id not in fetched_ids
    assert second_old_schedule.id not in fetched_ids
    assert first_latest_schedule.id in fetched_ids
    assert second_latest_schedule.id in fetched_ids
    assert fetched_3 is None
