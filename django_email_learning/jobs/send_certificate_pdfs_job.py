import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from django_email_learning.jobs.job_metrics import track_job_execution
from django_email_learning.jobs.queue_utils import resolve_queue
from django_email_learning.models import Certificate, JobExecution, JobName, JobStatus
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.services.certificate_pdf_service import generate_certificate_pdf
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


def _get_max_retries() -> int:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return int(conf.get("CERTIFICATES", {}).get("MAX_RETRIES", 3))


class SendCertificatePdfsJob:
    def __init__(self) -> None:
        self.certificate_pdf_queue: TaskQueueProtocol[Certificate] = self._get_certificate_pdf_queue()

    def run(self) -> None:
        job_execution = JobExecution.start_if_not_running(job_name=JobName.SEND_CERTIFICATE_PDFS.value)
        if job_execution is None:
            logger.warning("Another instance of SendCertificatePdfsJob is already running. Exiting this run.")
            return
        self._run_job(job_execution)

    @track_job_execution(
        metric_service=metric_service,
        job_name=JobName.SEND_CERTIFICATE_PDFS.value,
    )
    def _run_job(self, job_execution: JobExecution) -> None:
        while True:
            certificate = self.certificate_pdf_queue.next_task()
            if certificate is None:
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
                return
            self.process_certificate(certificate)

    def _get_certificate_pdf_queue(self) -> TaskQueueProtocol[Certificate]:
        from django_email_learning.services.defaults.database_certificate_pdf_queue import (
            DatabaseCertificatePdfQueue,
        )

        return resolve_queue("CERTIFICATE_PDF_QUEUE", DatabaseCertificatePdfQueue)

    def process_certificate(self, certificate: Certificate) -> None:
        try:
            self._send_certificate_email(certificate)
            certificate.pdf_email_status = Certificate.PdfEmailStatus.SENT
            certificate.pdf_email_sent_at = timezone.now()
            certificate.save(update_fields=["pdf_email_status", "pdf_email_sent_at"])
            logger.info(f"Certificate {certificate.id}: PDF email sent.")
        except Exception:
            logger.exception(f"Certificate {certificate.id}: failed to send PDF email.")
            certificate.pdf_email_retry_count += 1
            if certificate.pdf_email_retry_count >= _get_max_retries():
                certificate.pdf_email_status = Certificate.PdfEmailStatus.FAILED
                logger.error(
                    f"Certificate {certificate.id}: PDF email permanently failed "
                    f"after {certificate.pdf_email_retry_count} attempts."
                )
            else:
                certificate.pdf_email_status = Certificate.PdfEmailStatus.PENDING
            certificate.save(update_fields=["pdf_email_status", "pdf_email_retry_count"])

    def _send_certificate_email(self, certificate: Certificate) -> None:
        course = certificate.enrollment.course
        organization = course.organization
        learner = certificate.enrollment.learner

        pdf_bytes = generate_certificate_pdf(certificate)

        context = {
            "course_title": course.title,
            "organization_name": organization.name,
        }
        subject = _("Your Certificate of Completion")
        body = render_to_string("emails/certificate_issued.txt", context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_sender_service.from_email,
            to=[learner.email],
        )
        email.attach_alternative(render_to_string("emails/certificate_issued.html", context), "text/html")
        email.attach(f"certificate-{certificate.certificate_number}.pdf", pdf_bytes, "application/pdf")

        email_sender_service.send(email)
