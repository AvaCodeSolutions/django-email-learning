from unittest.mock import MagicMock, patch

import pytest

from django_email_learning.jobs.send_certificate_pdfs_job import SendCertificatePdfsJob
from django_email_learning.models import Certificate, JobExecution, JobName, JobStatus


@pytest.fixture()
def certificate(enrollment):
    return Certificate.objects.create(enrollment=enrollment, name_on_certificate="John Doe")


@pytest.fixture()
def certificate_pdf_queue_mock():
    return MagicMock()


@pytest.fixture()
def job(certificate_pdf_queue_mock):
    with patch(
        "django_email_learning.jobs.send_certificate_pdfs_job.SendCertificatePdfsJob._get_certificate_pdf_queue",
        return_value=certificate_pdf_queue_mock,
    ):
        j = SendCertificatePdfsJob()
    j.certificate_pdf_queue = certificate_pdf_queue_mock
    return j


def test_run_exits_when_already_running(db, job):
    with patch(
        "django_email_learning.jobs.send_certificate_pdfs_job.JobExecution.start_if_not_running",
        return_value=None,
    ):
        job.run()

    job.certificate_pdf_queue.next_task.assert_not_called()


def test_run_marks_job_completed_when_queue_empty(db, job):
    job.certificate_pdf_queue.next_task.return_value = None
    job.run()

    execution = JobExecution.objects.get(job_name=JobName.SEND_CERTIFICATE_PDFS.value)
    assert execution.status == JobStatus.COMPLETED.value


def test_process_certificate_success_marks_sent_and_attaches_pdf(db, certificate):
    with (
        patch(
            "django_email_learning.jobs.send_certificate_pdfs_job.generate_certificate_pdf",
            return_value=b"%PDF-1.4 fake pdf bytes",
        ),
        patch("django_email_learning.jobs.send_certificate_pdfs_job.email_sender_service.send") as send_mock,
    ):
        SendCertificatePdfsJob().process_certificate(certificate)

    certificate.refresh_from_db()
    assert certificate.pdf_email_status == Certificate.PdfEmailStatus.SENT
    assert certificate.pdf_email_sent_at is not None

    sent_email = send_mock.call_args[0][0]
    assert sent_email.to == [certificate.enrollment.learner.email]
    assert len(sent_email.attachments) == 1
    filename, content, mimetype = sent_email.attachments[0]
    assert filename == f"certificate-{certificate.certificate_number}.pdf"
    assert content == b"%PDF-1.4 fake pdf bytes"
    assert mimetype == "application/pdf"


def test_process_certificate_failure_increments_retry_and_sets_pending(db, certificate):
    with (
        patch(
            "django_email_learning.jobs.send_certificate_pdfs_job.generate_certificate_pdf",
            side_effect=RuntimeError("pdf generation failed"),
        ),
    ):
        SendCertificatePdfsJob().process_certificate(certificate)

    certificate.refresh_from_db()
    assert certificate.pdf_email_status == Certificate.PdfEmailStatus.PENDING
    assert certificate.pdf_email_retry_count == 1


def test_process_certificate_marks_failed_after_max_retries(db, certificate, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "CERTIFICATES": {"MAX_RETRIES": 1},
    }
    with patch(
        "django_email_learning.jobs.send_certificate_pdfs_job.generate_certificate_pdf",
        side_effect=RuntimeError("pdf generation failed"),
    ):
        SendCertificatePdfsJob().process_certificate(certificate)

    certificate.refresh_from_db()
    assert certificate.pdf_email_status == Certificate.PdfEmailStatus.FAILED
    assert certificate.pdf_email_retry_count == 1
