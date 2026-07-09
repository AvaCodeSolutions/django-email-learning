from django_email_learning.models import Certificate, Enrollment, Learner
from django_email_learning.services.defaults.database_certificate_pdf_queue import (
    DatabaseCertificatePdfQueue,
)


def test_next_task_returns_none_when_no_pending_certificates(db):
    queue = DatabaseCertificatePdfQueue()
    assert queue.next_task() is None


def test_next_task_claims_pending_certificate_and_marks_processing(db, enrollment):
    certificate = Certificate.objects.create(enrollment=enrollment, name_on_certificate="John Doe")
    assert certificate.pdf_email_status == Certificate.PdfEmailStatus.PENDING

    queue = DatabaseCertificatePdfQueue()
    task = queue.next_task()

    assert task is not None
    assert task.id == certificate.id
    certificate.refresh_from_db()
    assert certificate.pdf_email_status == Certificate.PdfEmailStatus.PROCESSING


def test_next_task_ignores_non_pending_certificates(db, enrollment):
    Certificate.objects.create(
        enrollment=enrollment,
        name_on_certificate="Already Sent",
        pdf_email_status=Certificate.PdfEmailStatus.SENT,
    )

    queue = DatabaseCertificatePdfQueue()
    assert queue.next_task() is None


def test_next_task_exhausts_batch_before_returning_none(db, course):
    for i in range(3):
        learner = Learner.objects.create(email=f"learner{i}@example.com", organization_id=course.organization_id)
        enrollment = Enrollment.objects.create(learner=learner, course=course, status="completed")
        Certificate.objects.create(enrollment=enrollment, name_on_certificate=f"Learner {i}")

    queue = DatabaseCertificatePdfQueue()
    queue.BATCH_SIZE = 2
    seen = []
    while True:
        task = queue.next_task()
        if task is None:
            break
        seen.append(task.id)

    assert len(seen) == 3
    assert len(set(seen)) == 3
