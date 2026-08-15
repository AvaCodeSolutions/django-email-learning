import datetime
import logging
from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.jobs.queue_utils import resolve_queue
from django_email_learning.models import (
    CourseContentType,
    DeliverySchedule,
    DeliveryStatus,
    JobExecution,
    JobName,
    JobStatus,
)
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.services.command_models.send_assignment_command import (
    AssignmentNotFoundError,
    SendAssignmentCommand,
)
from django_email_learning.services.command_models.send_lesson_command import (
    LessonNotFoundError,
    SendLessonCommand,
)
from django_email_learning.services.command_models.send_quiz_command import (
    QuizNotFoundError,
    SendQuizCommand,
)
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


def _get_delivery_workers() -> int:
    """Return the configured number of delivery worker threads (default 1)."""
    return int(getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DELIVERY_WORKERS", 1))


class DeliverContentsJob:
    def __init__(self, delivery_queue: TaskQueueProtocol[DeliverySchedule] | None = None) -> None:
        # A caller that only needs `process_delivery` for a schedule it has
        # already claimed can pass its own queue, so constructing the job does
        # not claim a batch of work the running job should be handling.
        self.delivery_queue: TaskQueueProtocol[DeliverySchedule] = (
            delivery_queue if delivery_queue is not None else self.get_delivery_queue()
        )

    def start(self) -> JobExecution | None:
        job_execution = JobExecution.start_if_not_running(job_name=JobName.DELIVER_CONTENTS.value)
        if job_execution is None:
            logger.warning("Another instance of DeliverContentsJob is already running. Exiting this run.")
        return job_execution

    def run(self) -> None:
        job_execution = self.start()
        if job_execution is not None:
            self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.DELIVER_CONTENTS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        workers = _get_delivery_workers()

        if workers <= 1:
            self._run_sequential(job_execution)
        else:
            logger.info(f"Starting delivery job with {workers} worker threads.")
            self._run_threaded(job_execution, workers)

    # ── sequential (original behaviour, workers=1) ──────────────────────────

    def _run_sequential(self, job_execution: JobExecution) -> None:
        while True:
            delivery_schedule = self.delivery_queue.next_task()
            if delivery_schedule is None:
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
                return
            try:
                self.process_delivery(delivery_schedule)
            except Exception as e:
                self.block_delivery(delivery_schedule, e)

    # ── threaded (workers > 1) ───────────────────────────────────────────────

    def _run_threaded(self, job_execution: JobExecution, workers: int) -> None:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures: dict[Future[None], DeliverySchedule] = {}
            exhausted = False

            while not exhausted or futures:
                # Submit new tasks while there is capacity and the queue is not empty
                while not exhausted and len(futures) < workers:
                    delivery_schedule = self.delivery_queue.next_task()
                    if delivery_schedule is None:
                        exhausted = True
                        break
                    future = executor.submit(self._worker, delivery_schedule)
                    futures[future] = delivery_schedule

                # Collect completed futures
                done = {f for f in futures if f.done()}
                for future in done:
                    delivery_schedule = futures.pop(future)
                    try:
                        future.result()
                    except Exception as e:
                        self.block_delivery(delivery_schedule, e)

                # Avoid a tight spin-wait when all workers are busy
                if not done and futures:
                    next(as_completed(futures), None)

        job_execution.status = JobStatus.COMPLETED.value
        job_execution.finished_at = timezone.now()
        job_execution.save()

    def _worker(self, delivery_schedule: DeliverySchedule) -> None:
        """Entry point for each worker thread."""
        # Each thread needs its own DB connection.
        close_old_connections()
        try:
            self.process_delivery(delivery_schedule)
        except Exception as e:
            self.block_delivery(delivery_schedule, e)
            raise

    def block_delivery(self, delivery_schedule: DeliverySchedule, exc: Exception) -> None:
        """Mark a delivery as BLOCKED and emit a metric."""
        delivery_schedule.status = DeliveryStatus.BLOCKED
        delivery_schedule.save()
        metric_service.delivery_schedule_blocked(delivery_schedule.delivery.course_content.id)
        logger.exception(f"Error processing delivery schedule {delivery_schedule.id}: {exc}. Marking as BLOCKED.")

    # ── queue / delivery logic (unchanged) ──────────────────────────────────

    def get_delivery_queue(self) -> TaskQueueProtocol[DeliverySchedule]:
        from django_email_learning.services.defaults.database_delivery_queue import (
            DatabaseDeliveryQueue,
        )

        return resolve_queue("DELIVERY_QUEUE", DatabaseDeliveryQueue)

    def process_delivery(self, delivery_schedule: DeliverySchedule) -> None:
        course_content = delivery_schedule.delivery.course_content
        if not course_content.is_published:
            logger.warning(f"CourseContent {course_content.id} is not published. Canceling the delivery.")
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            return

        if course_content.type == CourseContentType.LESSON:
            is_delivered = self.send_lesson_content(delivery_schedule)
            if is_delivered:
                logger.info(
                    f"Lesson content delivered for DeliverySchedule ID {delivery_schedule.id}. Scheduling next content."
                )
                next_delivery = delivery_schedule.delivery.schedule_next_delivery()
                enrollment_id = delivery_schedule.delivery.enrollment.id
                if next_delivery:
                    logger.info(f"Scheduled next delivery {next_delivery.id} for enrollment {enrollment_id}")
                else:
                    logger.info(f"No more content to schedule for enrollment {enrollment_id}")
                    delivery_schedule.delivery.enrollment.graduate()

        elif course_content.type == CourseContentType.QUIZ:
            is_delivered = self.send_quiz_content(delivery_schedule)

            # For quiz we don't schedule next content automatically,
            # because the scheduling should be done after quiz completion.
            if is_delivered:
                logger.info(
                    f"Quiz content delivered for DeliverySchedule ID {delivery_schedule.id}. "
                    "Next content scheduling is deferred until quiz completion."
                )
        elif course_content.type == CourseContentType.ASSIGNMENT and course_content.assignment is not None:
            is_delivered = self.send_assignment_content(delivery_schedule)

            # For assignment we don't schedule next content automatically,
            # because the scheduling should be done after assignment completion.
            if is_delivered:
                if not course_content.assignment.is_blocking:
                    logger.info(
                        f"Non-blocking assignment content "
                        f"delivered for DeliverySchedule ID {delivery_schedule.id}. Scheduling next content."
                    )
                    next_delivery = delivery_schedule.delivery.schedule_next_delivery()
                    enrollment_id = delivery_schedule.delivery.enrollment.id
                    if next_delivery:
                        logger.info(f"Scheduled next delivery {next_delivery.id} for enrollment {enrollment_id}")
                    else:
                        logger.info(f"No more content to schedule for enrollment {enrollment_id}")
                        delivery_schedule.delivery.enrollment.graduate()

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
                f"Lesson with ID {delivery_schedule.delivery.course_content.lesson.id} not found. "
                f"Canceling the delivery."
            )
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
        except Exception as e:
            logger.exception(f"Failed to send lesson content for DeliverySchedule ID {delivery_schedule.id}: {str(e)}")
            self.handle_failed_delivery(delivery_schedule)
        return False

    def send_quiz_content(self, delivery_schedule: DeliverySchedule) -> bool:
        if not delivery_schedule.delivery.course_content.quiz:
            delivery_schedule.status = DeliveryStatus.CANCELED
            delivery_schedule.save()
            logger.error(f"DeliverySchedule ID {delivery_schedule.id} has no associated quiz. Canceling the delivery.")
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
            logger.exception(f"Failed to send quiz content for DeliverySchedule ID {delivery_schedule.id}: {str(e)}")
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
                f"Assignment with ID {delivery_schedule.delivery.course_content.assignment.id} not found. "
                f"Canceling the delivery."
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
        # TODO: Add metric logging for rescheduled failed attempts.
        """Handle a failed delivery by rescheduling or blocking it."""
        if delivery_schedule.failed_attempts >= 3:
            logger.error(
                f"DeliverySchedule ID {delivery_schedule.id} has reached maximum retry attempts. Blocking the delivery."
            )
            delivery_schedule.status = DeliveryStatus.BLOCKED
            delivery_schedule.save()
            metric_service.delivery_schedule_blocked(delivery_schedule.delivery.course_content.id)
        else:
            delivery_schedule.time += datetime.timedelta(minutes=60)
            delivery_schedule.failed_attempts += 1
            delivery_schedule.status = DeliveryStatus.SCHEDULED
            delivery_schedule.save()
