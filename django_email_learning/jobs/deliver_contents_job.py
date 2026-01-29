from django_email_learning.ports.delivery_queue_protocol import DeliveryQueueProtocol
from django_email_learning.models import DeliverySchedule, DeliveryStatus
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
    LessonNotFoundError,
)
from django_email_learning.services.command_models.send_quiz_command import (
    SendQuizCommand,
    QuizNotFoundError,
)
from django_email_learning.models import JobExecution, JobName, JobStatus
from django.utils.module_loading import import_string
from django.conf import settings
from django.utils import timezone
import logging
import datetime


logger = logging.getLogger(__name__)


class DeliverContentsJob:
    def __init__(self) -> None:
        self.delivery_queue: DeliveryQueueProtocol = self.get_delivery_queue()

    def run(self) -> None:
        if JobExecution.objects.filter(
            job_name=JobName.DELIVER_CONTENTS.value,
            status=JobStatus.RUNNING.value,
        ).exists():
            logger.warning(
                "Another instance of DeliverContentsJob is already running. Exiting this run."
            )
            return
        job_execution = JobExecution.objects.create(
            job_name=JobName.DELIVER_CONTENTS.value,
            status=JobStatus.RUNNING.value,
            started_at=timezone.now(),
        )
        should_check_next = True
        while should_check_next:
            delivery_schedule = self.delivery_queue.next_task()
            if delivery_schedule is None:
                should_check_next = False
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
            else:
                self.process_delivery(delivery_schedule)

    def get_delivery_queue(self) -> DeliveryQueueProtocol:
        try:
            return import_string(settings.DJANGO_EMAIL_LEARNING["DELIVERY_QUEUE"])
        except (AttributeError, KeyError):
            from django_email_learning.services.defaults.database_delivery_queue import (
                DatabaseDeliveryQueue,
            )

            return DatabaseDeliveryQueue()

    def process_delivery(self, delivery_schedule: DeliverySchedule) -> None:
        course_content = delivery_schedule.delivery.course_content
        if not course_content.is_published:
            logger.warning(
                f"CourseCcontent {course_content.id} is not published. Canceling the delivery."
            )
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            return

        if course_content.type == "lesson":
            is_delivered = self.send_lesson_content(delivery_schedule)
            if is_delivered:
                logger.info(
                    f"Lesson content delivered for DeliverySchedule ID {delivery_schedule.id}. Scheduling next content."
                )
                next_delivery = delivery_schedule.delivery.schedule_next_delivery()
                if next_delivery:
                    logger.info(
                        f"Scheduled next delivery {next_delivery.id} for enrollment {delivery_schedule.delivery.enrollment.id}"
                    )
                else:
                    logger.info(
                        f"No more content to schedule for enrollment {delivery_schedule.delivery.enrollment.id}"
                    )
                    # TODO: if the sent content was the last in the course, consider marking the enrollment as completed.
                    delivery_schedule.delivery.enrollment.graduate()

        elif course_content.type == "quiz":
            is_delivered = self.send_quiz_content(delivery_schedule)

            # For quiz we don't schedule next content automatically, because the scheduling should be done after quiz completion.
            if is_delivered:
                logger.info(
                    f"Quiz content delivered for DeliverySchedule ID {delivery_schedule.id}. Next content scheduling is deferred until quiz completion."
                )

    def send_lesson_content(self, delivery_schedule: DeliverySchedule) -> bool:
        if not delivery_schedule.delivery.course_content.lesson:
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            logger.error(
                f"DeliverySchedule ID {delivery_schedule.id} has no associated lesson. Canceling the delivery."
            )
            return False

        try:
            command = SendLessonCommand(
                content_id=delivery_schedule.delivery.course_content.id,
                email=delivery_schedule.delivery.enrollment.learner.email,
            )
            command.execute()
            delivery_schedule.status = DeliveryStatus.DELIVERED
            delivery_schedule.save()
            return True

        except LessonNotFoundError:
            logger.error(
                f"Lesson with ID {delivery_schedule.delivery.course_content.lesson.id} not found. Canceling the delivery."
            )
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
        except Exception as e:
            logger.exception(
                f"Failed to send lesson content for DeliverySchedule ID {delivery_schedule.id}: {str(e)}"
            )
            self.handle_failed_delivery(delivery_schedule)
        return False

    def send_quiz_content(self, delivery_schedule: DeliverySchedule) -> bool:
        if not delivery_schedule.delivery.course_content.quiz:
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            logger.error(
                f"DeliverySchedule ID {delivery_schedule.id} has no associated quiz. Canceling the delivery."
            )
            return False

        try:
            if not delivery_schedule.link:
                link = delivery_schedule.generate_link()
                delivery_schedule.link = link
                delivery_schedule.save()

            command = SendQuizCommand(
                content_id=delivery_schedule.delivery.course_content.id,
                email=delivery_schedule.delivery.enrollment.learner.email,
                link=delivery_schedule.link,
            )
            command.execute()
            delivery_schedule.status = DeliveryStatus.DELIVERED
            delivery_schedule.save()

            return True
        except QuizNotFoundError:
            logger.error(
                f"Quiz with ID {delivery_schedule.delivery.course_content.quiz.id} not found. Canceling the delivery."
            )
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
        except Exception as e:
            logger.exception(
                f"Failed to send quiz content for DeliverySchedule ID {delivery_schedule.id}: {str(e)}"
            )
            self.handle_failed_delivery(delivery_schedule)
        return False

    def handle_failed_delivery(self, delivery_schedule: DeliverySchedule) -> None:
        # TODO: Implement custome metric logging for blocked deliveries and failed attempts.
        """Handle a failed delivery by rescheduling or blocking it."""
        if delivery_schedule.failed_attempts >= 3:
            logger.error(
                f"DeliverySchedule ID {delivery_schedule.id} has reached maximum retry attempts. Blocking the delivery."
            )
            delivery_schedule.status = DeliveryStatus.BLOCKED
            delivery_schedule.save()
        else:
            delivery_schedule.time += datetime.timedelta(minutes=60)
            delivery_schedule.failed_attempts += 1
            delivery_schedule.status = DeliveryStatus.SCHEDULED
            delivery_schedule.save()
