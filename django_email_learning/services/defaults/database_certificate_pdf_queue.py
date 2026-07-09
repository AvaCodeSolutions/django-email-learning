import logging
from typing import Iterator

from django.db import transaction

from django_email_learning.models import Certificate
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol

logger = logging.getLogger(__name__)


class DatabaseCertificatePdfQueue(TaskQueueProtocol[Certificate]):
    BATCH_SIZE = 50

    def __init__(self) -> None:
        self._iterator: Iterator[Certificate] = iter([])

    def _get_next_batch(self) -> Iterator[Certificate]:
        with transaction.atomic():
            certificate_ids = list(
                Certificate.objects.select_for_update(skip_locked=True)
                .filter(pdf_email_status=Certificate.PdfEmailStatus.PENDING)[: self.BATCH_SIZE]
                .values_list("id", flat=True)
            )

            if not certificate_ids:
                return iter([])

            logger.debug(f"DatabaseCertificatePdfQueue: {len(certificate_ids)} certificate(s) pending a PDF email.")
            Certificate.objects.filter(id__in=certificate_ids).update(
                pdf_email_status=Certificate.PdfEmailStatus.PROCESSING
            )

        return (
            Certificate.objects.filter(id__in=certificate_ids)
            .select_related("enrollment__learner", "enrollment__course__organization")
            .iterator(chunk_size=self.BATCH_SIZE)
        )

    def next_task(self) -> Certificate | None:
        try:
            return next(self._iterator)
        except StopIteration:
            self._iterator = self._get_next_batch()
            try:
                return next(self._iterator)
            except StopIteration:
                return None
