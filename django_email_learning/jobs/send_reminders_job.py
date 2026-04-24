from django_email_learning.ports.delivery_queue_protocol import DeliveryQueueProtocol
from django_email_learning.models import ContentDelivery, DeliverySchedule

from django_email_learning.services.metrics_service import MetricsService
from django_email_learning.models import JobExecution, JobName, JobStatus
from django_email_learning.services.command_models.send_quiz_reminder_command import (
    SendQuizReminderCommand,
    QuizNotFoundError,
)
from django.utils.module_loading import import_string
from django.conf import settings
from django.utils import timezone
import logging


logger = logging.getLogger(__name__)
METRIC_SERVICE = MetricsService()


class SendRemindersJob:
    def __init__(self) -> None:
        self.reminder_queue: DeliveryQueueProtocol = self.get_reminder_queue()

    def run(self) -> None:
        if JobExecution.objects.filter(
            job_name=JobName.SEND_REMINDERS.value,
            status=JobStatus.RUNNING.value,
        ).exists():
            logger.warning(
                "Another instance of SendRemindersJob is already running. Exiting this run."
            )
            return
        job_execution = JobExecution.objects.create(
            job_name=JobName.SEND_REMINDERS.value,
            status=JobStatus.RUNNING.value,
            started_at=timezone.now(),
        )
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

    def get_reminder_queue(self) -> DeliveryQueueProtocol:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            configured_reminder_queue = import_string(
                DJANGO_EMAIL_LEARNING_SETTINGS["REMINDER_QUEUE"]
            )
            return (
                configured_reminder_queue()
                if isinstance(configured_reminder_queue, type)
                else configured_reminder_queue
            )
        except KeyError:
            from django_email_learning.services.defaults.database_reminder_queue import (
                DatabaseReminderQueue,
            )

            return DatabaseReminderQueue()

    def process_reminder(self, delivery_schedule: DeliverySchedule) -> None:
        try:
            command = SendQuizReminderCommand(
                delivery_schedule=delivery_schedule,
            )
            command.execute()
            delivery_schedule.delivery.reminder_state = (
                ContentDelivery.ReminderStatus.SENT
            )
            delivery_schedule.delivery.save()
        except QuizNotFoundError as e:
            logger.error(
                f"Quiz not found for CourseContent ID {delivery_schedule.delivery.course_content.id}: {str(e)}. Marking reminder as not applicable."
            )
            delivery_schedule.delivery.reminder_state = (
                ContentDelivery.ReminderStatus.NOT_APPLICABLE
            )
            delivery_schedule.delivery.save()
        except Exception as e:
            logger.exception(
                f"Unexpected error processing reminder for DeliverySchedule ID {delivery_schedule.id}: {str(e)}. Marking reminder as blocked."
            )
            delivery_schedule.delivery.reminder_state = (
                ContentDelivery.ReminderStatus.BLOCKED
            )
            delivery_schedule.delivery.save()
            METRIC_SERVICE.reminder_schedule_blocked(
                delivery_schedule.delivery.course_content.id
            )
