from unittest.mock import patch

import pytest
import django_email_learning.jobs.send_reminders_job as send_reminders_job_module
from django_email_learning.jobs.send_reminders_job import (
    SendRemindersJob,
    SendQuizReminderCommand,
    QuizNotFoundError,
)
from django_email_learning.services.command_models.send_assignment_reminder_command import (
    SendAssignmentReminderCommand,
)
from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    EnrollmentStatus,
    JobExecution,
    JobName,
    JobStatus,
)
from tests.jobs.delivery_queue_mock import DeliveryQueueMock


@pytest.fixture
def reminder_queue_mock():
    mock = DeliveryQueueMock()
    with patch(
        "django_email_learning.services.defaults.database_reminder_queue.DatabaseReminderQueue",
        return_value=mock,
    ):
        yield mock


def test_send_reminders_job_runs_no_tasks(db, reminder_queue_mock):
    job = SendRemindersJob()
    job.run()
    assert reminder_queue_mock.index == 0


def test_send_reminders_job_runs_with_tasks(
    db, reminder_queue_mock, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=delivery)

    reminder_queue_mock.add_task(delivery_schedule)

    with patch.object(SendQuizReminderCommand, "execute", return_value=None):
        job = SendRemindersJob()
        job.run()

    delivery.refresh_from_db()
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
    assert reminder_queue_mock.index == 1


def test_send_reminders_job_marks_not_applicable_when_quiz_not_found(
    db, reminder_queue_mock, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=delivery)

    reminder_queue_mock.add_task(delivery_schedule)

    with patch.object(
        SendQuizReminderCommand,
        "execute",
        side_effect=QuizNotFoundError("No quiz found"),
    ):
        job = SendRemindersJob()
        job.run()

    delivery.refresh_from_db()
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.NOT_APPLICABLE


def test_send_reminders_job_triggers_started_metric(db, reminder_queue_mock):
    with patch.object(
        send_reminders_job_module.metric_service,
        "job_execution_started",
    ) as metric_started_spy:
        job = SendRemindersJob()
        job.run()

    metric_started_spy.assert_called_once_with(job_name="send_reminders")


def test_send_reminders_job_triggers_finished_metric(db, reminder_queue_mock):
    with patch.object(
        send_reminders_job_module.metric_service,
        "job_execution_finished",
    ) as metric_finished_spy:
        job = SendRemindersJob()
        job.run()

    metric_finished_spy.assert_called_once()
    call_kwargs = metric_finished_spy.call_args
    assert call_kwargs.kwargs["job_name"] == "send_reminders"
    assert isinstance(call_kwargs.kwargs["execution_time"], int)


def test_send_reminders_job_blocks_on_unexpected_exception_and_tracks_metric(
    db, reminder_queue_mock, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=delivery)

    reminder_queue_mock.add_task(delivery_schedule)

    with (
        patch.object(
            SendQuizReminderCommand,
            "execute",
            side_effect=Exception("Simulated reminder failure"),
        ),
        patch.object(
            send_reminders_job_module.metric_service,
            "reminder_schedule_blocked",
        ) as metric_blocked_spy,
    ):
        job = SendRemindersJob()
        job.run()

    delivery.refresh_from_db()
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.BLOCKED
    metric_blocked_spy.assert_called_once_with(
        delivery_schedule.delivery.course_content.id
    )


def test_send_reminders_job_does_not_emit_start_or_finish_metrics_when_already_running(
    db, reminder_queue_mock
):
    JobExecution.objects.create(
        job_name=JobName.SEND_REMINDERS.value,
        status=JobStatus.RUNNING.value,
    )

    with (
        patch.object(
            send_reminders_job_module.metric_service,
            "job_execution_started",
        ) as metric_started_spy,
        patch.object(
            send_reminders_job_module.metric_service,
            "job_execution_finished",
        ) as metric_finished_spy,
    ):
        SendRemindersJob().run()

    metric_started_spy.assert_not_called()
    metric_finished_spy.assert_not_called()


def test_send_reminders_job_uses_quiz_reminder_command_for_quiz_content(
    db, reminder_queue_mock, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=delivery)

    reminder_queue_mock.add_task(delivery_schedule)

    with (
        patch.object(
            SendQuizReminderCommand, "execute", return_value=None
        ) as quiz_execute,
        patch.object(
            SendAssignmentReminderCommand, "execute", return_value=None
        ) as assignment_execute,
    ):
        job = SendRemindersJob()
        job.run()

    quiz_execute.assert_called_once()
    assignment_execute.assert_not_called()


def test_send_reminders_job_uses_assignment_reminder_command_for_assignment_content(
    db, reminder_queue_mock, enrollment, course_assignment_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
        reminder_state=ContentDelivery.ReminderStatus.PENDING,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=delivery)

    reminder_queue_mock.add_task(delivery_schedule)

    with (
        patch.object(
            SendAssignmentReminderCommand, "execute", return_value=None
        ) as assignment_execute,
        patch.object(
            SendQuizReminderCommand, "execute", return_value=None
        ) as quiz_execute,
    ):
        job = SendRemindersJob()
        job.run()

    assignment_execute.assert_called_once()
    quiz_execute.assert_not_called()
    delivery.refresh_from_db()
    assert delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
