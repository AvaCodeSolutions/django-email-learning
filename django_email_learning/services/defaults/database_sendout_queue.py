import logging
from typing import Iterator

from django.db import transaction
from django.utils import timezone

from django_email_learning.models import Sendout
from django_email_learning.ports.sendout_queue_protocol import SendoutQueueProtocol

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class DatabaseSendoutQueue(SendoutQueueProtocol):
    def __init__(self) -> None:
        self._task_iterator: Iterator[Sendout] = self._get_batch()

    def _get_batch(self) -> Iterator[Sendout]:
        with transaction.atomic():
            ids = list(
                Sendout.objects.select_for_update(skip_locked=True)
                .filter(
                    status=Sendout.Status.SCHEDULED,
                    scheduled_at__lte=timezone.now(),
                )[:BATCH_SIZE]
                .values_list("id", flat=True)
            )

        if not ids:
            return iter([])

        logger.debug(f"DatabaseSendoutQueue: Found {len(ids)} due sendouts.")
        return (
            Sendout.objects.filter(id__in=ids)
            .select_related("newsletter__organization")
            .prefetch_related("newsletter__subscribers")
            .iterator(chunk_size=BATCH_SIZE)
        )

    def next_task(self) -> Sendout | None:
        try:
            return next(self._task_iterator)
        except StopIteration:
            self._task_iterator = self._get_batch()
            try:
                return next(self._task_iterator)
            except StopIteration:
                return None
