from django_email_learning.ports.delivery_queue_protocol import DeliveryQueueProtocol
from django_email_learning.models import DeliverySchedule, DeliveryStatus
from django.db import transaction
from django.utils import timezone
from typing import Iterator


class DatabaseDeliveryQueue(DeliveryQueueProtocol):
    ITERATOR_BATCH_SIZE = 50

    def __init__(self) -> None:
        self._task_iterator = self.get_next_batch(limit=self.ITERATOR_BATCH_SIZE)

    def get_next_batch(self, limit: int) -> Iterator[DeliverySchedule]:
        with transaction.atomic():
            # Get IDs of ready tasks while locked
            task_ids = list(
                DeliverySchedule.objects.select_for_update(skip_locked=True)  # type: ignore[misc]
                .filter(status=DeliveryStatus.SCHEDULED, time__lte=timezone.now())[
                    :limit
                ]
                .values_list("id", flat=True)
            )

            if not task_ids:
                return iter([])

            # Update status
            DeliverySchedule.objects.filter(id__in=task_ids).update(
                status=DeliveryStatus.PROCESSING
            )

        # Return fresh objects outside transaction
        return (
            DeliverySchedule.objects.filter(id__in=task_ids)
            .select_related("delivery__enrollment__learner", "delivery__course_content")
            .iterator()
        )

    def next_task(self) -> DeliverySchedule | None:
        try:
            return next(self._task_iterator)
        except StopIteration:
            self._task_iterator = self.get_next_batch(limit=self.ITERATOR_BATCH_SIZE)
            try:
                return next(self._task_iterator)
            except StopIteration:
                return None
