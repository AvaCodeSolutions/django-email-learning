import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.jobs.queue_utils import resolve_queue
from django_email_learning.models import (
    JobExecution,
    JobName,
    JobStatus,
    Sendout,
    SendoutDelivery,
)
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
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
        self.sendout_queue: TaskQueueProtocol[
            SendoutDelivery
        ] = self._get_sendout_queue()

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

    def _get_sendout_queue(self) -> TaskQueueProtocol[SendoutDelivery]:
        from django_email_learning.services.defaults.database_sendout_queue import (
            DatabaseSendoutQueue,
        )

        return resolve_queue("SENDOUT_QUEUE", DatabaseSendoutQueue)

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
        """Mark the sendout as SENT once no actionable deliveries remain (best-effort).

        If every delivery permanently failed (zero sent) the sendout is kept as
        SCHEDULED and all failed deliveries are reset to PENDING so the next job
        run retries them — this signals a configuration-level issue rather than
        individual bad addresses.
        """
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

        if still_active or retryable_failures:
            return

        any_sent = sendout.deliveries.filter(
            status=SendoutDelivery.Status.SENT
        ).exists()
        if any_sent:
            sendout.status = Sendout.Status.SENT
            sendout.sent_at = timezone.now()
            sendout.save()
            logger.info(f"Sendout {sendout.id} marked as sent (best-effort).")
        else:
            logger.error(
                f"Sendout {sendout.id} for newsletter {sendout.newsletter_id}: "
                "all deliveries permanently failed — possible email configuration issue. "
                "Resetting deliveries for retry."
            )
            metric_service.sendout_all_deliveries_failed(
                sendout_id=sendout.id,
                newsletter_id=sendout.newsletter_id,
            )
            sendout.deliveries.filter(status=SendoutDelivery.Status.FAILED).update(
                status=SendoutDelivery.Status.PENDING,
                retry_count=0,
            )
            sendout.scheduled_at = timezone.now() + timedelta(minutes=10)
            sendout.save(update_fields=["scheduled_at"])

    def _send_to_subscriber(
        self, sendout: Sendout, email: str, unsubscribe_token: object
    ) -> None:
        try:
            unsubscribe_url = reverse(
                "django_email_learning:public:newsletter_unsubscribe",
                kwargs={"token": unsubscribe_token},
            )
            conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
            base_url: str = conf.get("SITE_BASE_URL", "")
            full_unsubscribe_url = f"{base_url.rstrip('/')}{unsubscribe_url}"
        except Exception:
            full_unsubscribe_url = ""

        plain_body = (
            f"{sendout.body}\n\n---\nTo unsubscribe, visit: {full_unsubscribe_url}"
            if full_unsubscribe_url
            else sendout.body
        )

        context = {
            "subject": sendout.subject,
            "body": sendout.body,
            "newsletter_title": sendout.newsletter.title,
            "unsubscribe_url": full_unsubscribe_url,
        }

        msg = EmailMultiAlternatives(
            subject=sendout.subject,
            body=plain_body,
            from_email=_get_newsletter_from_email(),
            to=[email],
        )
        msg.attach_alternative(
            render_to_string("emails/newsletter_sendout.html", context), "text/html"
        )
        email_sender_service.send(msg)
