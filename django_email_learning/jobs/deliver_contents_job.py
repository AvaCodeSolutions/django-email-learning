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
from django_email_learning.services.command_models.send_assignment_command import (
    SendAssignmentCommand,
    AssignmentNotFoundError,
)
from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.services.metrics_service import metric_service
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
        job_execution = JobExecution.start_if_not_running(
            job_name=JobName.DELIVER_CONTENTS.value
        )
        if job_execution is None:
            logger.warning(
                "Another instance of DeliverContentsJob is already running. Exiting this run."
            )
            return
        self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.DELIVER_CONTENTS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        should_check_next = True
        while should_check_next:
            delivery_schedule = self.delivery_queue.next_task()
            if delivery_schedule is None:
                should_check_next = False
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
            else:
                try:
                    self.process_delivery(delivery_schedule)
                except Exception as e:
                    # Unhandled exception during delivery processing should not crash the job.
                    # We log the error and mark the delivery as blocked to prevent further attempts until manual intervention.
                    delivery_schedule.status = DeliveryStatus.BLOCKED
                    delivery_schedule.save()
                    metric_service.delivery_schedule_blocked(
                        delivery_schedule.delivery.course_content.id
                    )
                    logger.exception(
                        f"Error processing delivery schedule: {str(e)}. Continuing with next task."
                    )

    def get_delivery_queue(self) -> DeliveryQueueProtocol:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            configured_delivery_queue = import_string(
                DJANGO_EMAIL_LEARNING_SETTINGS["DELIVERY_QUEUE"]
            )
            return (
                configured_delivery_queue()
                if isinstance(configured_delivery_queue, type)
                else configured_delivery_queue
            )
        except KeyError:
            from django_email_learning.services.defaults.database_delivery_queue import (
                DatabaseDeliveryQueue,
            )

            return DatabaseDeliveryQueue()

    def process_delivery(self, delivery_schedule: DeliverySchedule) -> None:
        course_content = delivery_schedule.delivery.course_content
        if not course_content.is_published:
            logger.warning(
                f"CourseContent {course_content.id} is not published. Canceling the delivery."
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
        elif (
            course_content.type == "assignment"
            and course_content.assignment is not None
        ):
            is_delivered = self.send_assignment_content(delivery_schedule)

            # For assignment we don't schedule next content automatically, because the scheduling should be done after assignment completion.
            if is_delivered:
                if not course_content.assignment.is_blocking:
                    # reschedule next content immediately for non-blocking assignments, For blocking assignments, the next content will be scheduled after the submission approval.
                    logger.info(
                        f"Non-blocking assignment content delivered for DeliverySchedule ID {delivery_schedule.id}. Scheduling next content."
                    )
                    next_delivery = delivery_schedule.delivery.schedule_next_delivery()
                    if next_delivery:
                        logger.info(
                            f"Scheduled next delivery {next_delivery.id} for enrollment {delivery_schedule.delivery.enrollment.id}"
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

    def send_assignment_content(self, delivery_schedule: DeliverySchedule) -> bool:
        if not delivery_schedule.delivery.course_content.assignment:
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            logger.error(
                f"DeliverySchedule ID {delivery_schedule.id} has no associated assignment. Canceling the delivery."
            )
            return False

        try:
            if not delivery_schedule.link:
                link = delivery_schedule.generate_link()
                delivery_schedule.link = link
                delivery_schedule.save()

            command = SendAssignmentCommand(
                content_id=delivery_schedule.delivery.course_content.id,
                email=delivery_schedule.delivery.enrollment.learner.email,
                link=delivery_schedule.link,
            )
            command.execute()
            delivery_schedule.status = DeliveryStatus.DELIVERED
            delivery_schedule.save()

            return True
        except AssignmentNotFoundError:
            logger.error(
                f"Assignment with ID {delivery_schedule.delivery.course_content.assignment.id} not found. Canceling the delivery."
            )
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
        except Exception as e:
            logger.exception(
                f"Failed to send assignment content for DeliverySchedule ID {delivery_schedule.id}: {str(e)}"
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
            metric_service.delivery_schedule_blocked(
                delivery_schedule.delivery.course_content.id
            )
        else:
            delivery_schedule.time += datetime.timedelta(minutes=60)
            delivery_schedule.failed_attempts += 1
            delivery_schedule.status = DeliveryStatus.SCHEDULED
            delivery_schedule.save()
