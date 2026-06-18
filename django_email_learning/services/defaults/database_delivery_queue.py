import threading
from typing import Iterator

from django.db import transaction
from django.utils import timezone

from django_email_learning.models import DeliverySchedule, DeliveryStatus
from django_email_learning.ports.delivery_queue_protocol import DeliveryQueueProtocol


class DatabaseDeliveryQueue(DeliveryQueueProtocol):
    """
    Thread-safe delivery queue backed by the database.

    Each call to ``next_task()`` is protected by a lock so that concurrent
    workers cannot advance the same iterator simultaneously.  The underlying
    ``SELECT FOR UPDATE SKIP LOCKED`` ensures that two workers can never claim
    the same ``DeliverySchedule`` row even if they enter ``get_next_batch``
    at the same time.
    """

    ITERATOR_BATCH_SIZE = 50

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._task_iterator: Iterator[DeliverySchedule] = self.get_next_batch(
            limit=self.ITERATOR_BATCH_SIZE
        )

    def get_next_batch(self, limit: int) -> Iterator[DeliverySchedule]:
        with transaction.atomic():
            # Atomically claim a batch of ready tasks.
            # skip_locked=True means concurrent workers skip rows already
            # locked by another transaction instead of waiting for them.
            task_ids = list(
                DeliverySchedule.objects.select_for_update(skip_locked=True)  # type: ignore[misc]
                .filter(status=DeliveryStatus.SCHEDULED, time__lte=timezone.now())[
                    :limit
                ]
                .values_list("id", flat=True)
            )

            if not task_ids:
                return iter([])

            DeliverySchedule.objects.filter(id__in=task_ids).update(
                status=DeliveryStatus.PROCESSING
            )

        # Return fully-hydrated objects outside the transaction so the lock
        # is released before we start iterating.
        return (
            DeliverySchedule.objects.filter(id__in=task_ids)
            .select_related(
                "delivery__enrollment__learner",
                "delivery__course_content__course__organization",
                "delivery__course_content__course__imap_connection",
                "delivery__course_content__lesson",
                "delivery__course_content__quiz",
                "delivery__course_content__assignment",
            )
            .prefetch_related("delivery__course_content__quiz__questions")
            .iterator(chunk_size=self.ITERATOR_BATCH_SIZE)
        )

    def next_task(self) -> DeliverySchedule | None:
        with self._lock:
            try:
                return next(self._task_iterator)
            except StopIteration:
                self._task_iterator = self.get_next_batch(
                    limit=self.ITERATOR_BATCH_SIZE
                )
                try:
                    return next(self._task_iterator)
                except StopIteration:
                    return None
