import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone
from django.utils.module_loading import import_string

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.models import (
    JobExecution,
    JobName,
    JobStatus,
    Sendout,
    SendoutDelivery,
)
from django_email_learning.ports.sendout_queue_protocol import SendoutQueueProtocol
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)

_DEFAULT_FROM_EMAIL = "webmaster@localhost"


def _get_newsletter_from_email() -> str:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return (
        conf.get("NEWSLETTERS", {}).get("FROM_EMAIL")
        or conf.get("FROM_EMAIL")
        or _DEFAULT_FROM_EMAIL
    )


def _get_max_retries() -> int:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return int(conf.get("NEWSLETTERS", {}).get("MAX_RETRIES", 3))


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
            delivery = self.sendout_queue.next_task()
            if delivery is None:
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
                return
            self.process_delivery(delivery)

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

    def process_delivery(self, delivery: SendoutDelivery) -> None:
        try:
            self._send_to_subscriber(
                delivery.sendout,
                delivery.subscriber.email,
                delivery.subscriber.unsubscribe_token,
            )
            delivery.status = SendoutDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.save()
            logger.info(
                f"Sendout {delivery.sendout_id}: sent to {delivery.subscriber.email}"
            )
        except Exception:
            logger.exception(
                f"Sendout {delivery.sendout_id}: failed to send to {delivery.subscriber.email}"
            )
            delivery.retry_count += 1
            max_retries = _get_max_retries()
            if delivery.retry_count >= max_retries:
                delivery.status = SendoutDelivery.Status.FAILED
                logger.error(
                    f"Sendout {delivery.sendout_id}: delivery to {delivery.subscriber.email} "
                    f"permanently failed after {delivery.retry_count} attempts."
                )
            else:
                delivery.status = SendoutDelivery.Status.PENDING
            delivery.save()

        self._maybe_complete_sendout(delivery.sendout)

    def _maybe_complete_sendout(self, sendout: Sendout) -> None:
        """Mark the sendout as SENT once no actionable deliveries remain (best-effort)."""
        max_retries = _get_max_retries()
        still_active = sendout.deliveries.filter(
            status__in=[
                SendoutDelivery.Status.PENDING,
                SendoutDelivery.Status.PROCESSING,
            ]
        ).exists()
        retryable_failures = sendout.deliveries.filter(
            status=SendoutDelivery.Status.FAILED,
            retry_count__lt=max_retries,
        ).exists()

        if not still_active and not retryable_failures:
            sendout.status = Sendout.Status.SENT
            sendout.sent_at = timezone.now()
            sendout.save()
            logger.info(f"Sendout {sendout.id} marked as sent (best-effort).")

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

        body = (
            f"{sendout.body}\n\n---\nTo unsubscribe, visit: {full_unsubscribe_url}"
            if full_unsubscribe_url
            else sendout.body
        )

        msg = EmailMultiAlternatives(
            subject=sendout.subject,
            body=body,
            from_email=_get_newsletter_from_email(),
            to=[email],
        )
        email_sender_service.send(msg)
