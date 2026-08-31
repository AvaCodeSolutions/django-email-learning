import logging

from django.utils import timezone

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.jobs.queue_utils import resolve_queue
from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    JobExecution,
    JobName,
    JobStatus,
)
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.services.command_models.send_assignment_reminder_command import (
    SendAssignmentReminderCommand,
)
from django_email_learning.services.command_models.send_quiz_reminder_command import (
    QuizNotFoundError,
    SendQuizReminderCommand,
)
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


class SendRemindersJob:
    def __init__(self) -> None:
        # Lazy: the default queue claims a batch as soon as it is built, and
        # `run()` exits without processing anything when another instance holds
        # the run lock. Anything claimed before that would never be released.
        self._reminder_queue: TaskQueueProtocol[DeliverySchedule] | None = None

    @property
    def reminder_queue(self) -> TaskQueueProtocol[DeliverySchedule]:
        if self._reminder_queue is None:
            self._reminder_queue = self.get_reminder_queue()
        return self._reminder_queue

    @reminder_queue.setter
    def reminder_queue(self, queue: TaskQueueProtocol[DeliverySchedule]) -> None:
        self._reminder_queue = queue

    def start(self) -> JobExecution | None:
        job_execution = JobExecution.start_if_not_running(job_name=JobName.SEND_REMINDERS.value)
        if job_execution is None:
            logger.warning("Another instance of SendRemindersJob is already running. Exiting this run.")
        return job_execution

    def run(self) -> None:
        job_execution = self.start()
        if job_execution is not None:
            self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.SEND_REMINDERS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        should_check_next = True
        while should_check_next:
            delivery_schedule = self.reminder_queue.next_task()
            if delivery_schedule is None:
                should_check_next = False
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
            else:
                self.process_reminder(delivery_schedule)

    def get_reminder_queue(self) -> TaskQueueProtocol[DeliverySchedule]:
        from django_email_learning.services.defaults.database_reminder_queue import (
            DatabaseReminderQueue,
        )

        return resolve_queue("REMINDER_QUEUE", DatabaseReminderQueue)

    def process_reminder(self, delivery_schedule: DeliverySchedule) -> None:
        try:
            if delivery_schedule.delivery.course_content.quiz:
                command = SendQuizReminderCommand(
                    delivery_schedule=delivery_schedule,
                )
            elif delivery_schedule.delivery.course_content.assignment:
                command = SendAssignmentReminderCommand(  # type: ignore[assignment]
                    delivery_schedule=delivery_schedule,
                )
            else:
                logger.error(
                    f"Delivery with ID {delivery_schedule.delivery.id} has no associated quiz or assignment. "
                    f"Marking reminder as not applicable."
                )
                delivery_schedule.delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE
                delivery_schedule.delivery.save()
                return
            command.execute()
            # `command.execute()` calls `delivery.record_reminder_sent()` on a
            # successful send, which advances `reminder_state` (to SENT, or back
            # to PENDING for deadline-less content that still has nudges left).
        except QuizNotFoundError as e:
            logger.error(
                f"Quiz not found for CourseContent ID {delivery_schedule.delivery.course_content.id}: {str(e)}. "
                f"Marking reminder as not applicable."
            )
            delivery_schedule.delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE
            delivery_schedule.delivery.save()
        except Exception as e:
            logger.exception(
                f"Unexpected error processing reminder for DeliverySchedule ID {delivery_schedule.id}: {str(e)}. "
                f"Marking reminder as blocked."
            )
            delivery_schedule.delivery.reminder_state = ContentDelivery.ReminderStatus.BLOCKED
            delivery_schedule.delivery.save()
            metric_service.reminder_schedule_blocked(delivery_schedule.delivery.course_content.id)
