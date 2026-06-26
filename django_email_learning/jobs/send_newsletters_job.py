import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.models import JobExecution, JobName, JobStatus, Sendout
from django_email_learning.ports.sendout_queue_protocol import SendoutQueueProtocol
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


class SendNewslettersJob:
    def __init__(self) -> None:
        self.sendout_queue: SendoutQueueProtocol = self._get_sendout_queue()

    def run(self) -> None:
        job_execution = JobExecution.start_if_not_running(
            job_name=JobName.SEND_NEWSLETTERS.value
        )
        if job_execution is None:
            logger.warning(
                "Another instance of SendNewslettersJob is already running. Exiting this run."
            )
            return
        self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.SEND_NEWSLETTERS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        while True:
            sendout = self.sendout_queue.next_task()
            if sendout is None:
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
                return
            self.process_sendout(sendout)

    def _get_sendout_queue(self) -> SendoutQueueProtocol:
        django_email_learning_settings: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            configured_queue = import_string(
                django_email_learning_settings["SENDOUT_QUEUE"]
            )
            return (
                configured_queue()
                if isinstance(configured_queue, type)
                else configured_queue
            )
        except KeyError:
            from django_email_learning.services.defaults.database_sendout_queue import (
                DatabaseSendoutQueue,
            )

            return DatabaseSendoutQueue()

    def process_sendout(self, sendout: Sendout) -> None:
        subscribers = list(sendout.newsletter.subscribers.all())
        if not subscribers:
            logger.info(f"Sendout {sendout.id} has no subscribers. Marking as sent.")
            sendout.status = Sendout.Status.SENT
            sendout.sent_at = timezone.now()
            sendout.save()
            return

        failed_emails: list[str] = []
        for subscriber in subscribers:
            try:
                self._send_to_subscriber(
                    sendout, subscriber.email, subscriber.unsubscribe_token
                )
                logger.info(f"Sendout {sendout.id}: sent to {subscriber.email}")
            except Exception:
                logger.exception(
                    f"Sendout {sendout.id}: failed to send to {subscriber.email}"
                )
                failed_emails.append(subscriber.email)

        if not failed_emails:
            sendout.status = Sendout.Status.SENT
            sendout.sent_at = timezone.now()
            sendout.save()
            logger.info(f"Sendout {sendout.id} completed successfully.")
        else:
            logger.error(
                f"Sendout {sendout.id}: {len(failed_emails)} delivery failures. "
                f"retry_count={sendout.retry_count}, max_retries={sendout.max_retries}"
            )
            if sendout.retry_count >= sendout.max_retries:
                sendout.status = Sendout.Status.FAILED
                sendout.save()
                logger.error(
                    f"Sendout {sendout.id} exceeded max retries. Marking as failed."
                )
            else:
                sendout.retry_count += 1
                sendout.save()
                logger.info(
                    f"Sendout {sendout.id} re-queued for retry "
                    f"({sendout.retry_count}/{sendout.max_retries})."
                )

    def _send_to_subscriber(
        self, sendout: Sendout, email: str, unsubscribe_token: object
    ) -> None:
        try:
            unsubscribe_url = reverse(
                "django_email_learning:newsletter_unsubscribe",
                kwargs={"token": unsubscribe_token},
            )
            conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
            base_url: str = conf.get("BASE_URL", "")
            full_unsubscribe_url = f"{base_url.rstrip('/')}{unsubscribe_url}"
        except Exception:
            full_unsubscribe_url = ""

        body_with_unsubscribe = (
            f"{sendout.body}\n\n---\nTo unsubscribe, visit: {full_unsubscribe_url}"
            if full_unsubscribe_url
            else sendout.body
        )

        msg = EmailMultiAlternatives(
            subject=sendout.subject,
            body=body_with_unsubscribe,
            to=[email],
        )
        email_sender_service.send(msg)
