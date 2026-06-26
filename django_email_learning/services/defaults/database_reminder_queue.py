from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.models import (
    DeliverySchedule,
    DeliveryStatus,
    ContentDelivery,
)
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from typing import Iterator
import logging

logger = logging.getLogger(__name__)


class DatabaseReminderQueue(TaskQueueProtocol[DeliverySchedule]):
    ITERATOR_BATCH_SIZE = 50

    def __init__(self) -> None:
        self._task_iterator = self.get_next_batch(limit=self.ITERATOR_BATCH_SIZE)

    def get_next_batch(self, limit: int) -> Iterator[DeliverySchedule]:
        with transaction.atomic():
            # Get IDs of ready tasks while locked
            task_ids = list(
                ContentDelivery.objects.select_for_update(skip_locked=True)  # type: ignore[misc]
                .filter(
                    delivery_schedules__status=DeliveryStatus.DELIVERED,
                    remind_at__lte=timezone.now(),
                    reminder_state=ContentDelivery.ReminderStatus.PENDING,
                )[:limit]
                .values_list("id", flat=True)
            )

            logger.debug(
                f"DatabaseReminderQueue: Found {len(task_ids)} ready reminder tasks."
            )

            if not task_ids:
                return iter([])

            # Update status
            ContentDelivery.objects.filter(id__in=task_ids).update(
                reminder_state=ContentDelivery.ReminderStatus.PROCESSING
            )

        # Return fresh objects outside transaction
        latest_schedule_id_subquery = (
            DeliverySchedule.objects.filter(delivery_id=OuterRef("delivery_id"))
            .order_by("-time", "-id")
            .values("id")[:1]
        )

        return (
            DeliverySchedule.objects.filter(delivery__id__in=task_ids)
            .filter(id=Subquery(latest_schedule_id_subquery))
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
        try:
            return next(self._task_iterator)
        except StopIteration:
            self._task_iterator = self.get_next_batch(limit=self.ITERATOR_BATCH_SIZE)
            try:
                return next(self._task_iterator)
            except StopIteration:
                return None
