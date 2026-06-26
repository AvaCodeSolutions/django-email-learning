import logging
from typing import Iterator

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from django_email_learning.models import Sendout, SendoutDelivery, NewsletterSubscriber
from django_email_learning.ports.sendout_queue_protocol import SendoutQueueProtocol

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


def get_max_retries() -> int:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return int(conf.get("NEWSLETTERS", {}).get("MAX_RETRIES", 3))


class DatabaseSendoutQueue(SendoutQueueProtocol):
    def __init__(self) -> None:
        self._iterator: Iterator[SendoutDelivery] = iter([])

    def _fanout_and_get_batch(self) -> Iterator[SendoutDelivery]:
        # Step 1: claim a batch of due sendouts
        with transaction.atomic():
            due_ids = list(
                Sendout.objects.select_for_update(skip_locked=True)
                .filter(
                    status=Sendout.Status.SCHEDULED,
                    scheduled_at__lte=timezone.now(),
                )
                .values_list("id", flat=True)[:BATCH_SIZE]
            )

        if not due_ids:
            return iter([])

        logger.debug(f"DatabaseSendoutQueue: {len(due_ids)} due sendout(s) found.")

        # Step 2: lazy fan-out — create a SendoutDelivery for every current subscriber
        # that doesn't already have one (idempotent via ignore_conflicts).
        for sendout_id in due_ids:
            subscriber_ids = list(
                NewsletterSubscriber.objects.filter(
                    newsletter__sendouts__id=sendout_id
                ).values_list("id", flat=True)
            )
            if subscriber_ids:
                SendoutDelivery.objects.bulk_create(
                    [
                        SendoutDelivery(sendout_id=sendout_id, subscriber_id=sid)
                        for sid in subscriber_ids
                    ],
                    ignore_conflicts=True,
                )

        # Step 3: lock and mark PROCESSING a batch of actionable deliveries
        max_retries = get_max_retries()
        with transaction.atomic():
            delivery_ids = list(
                SendoutDelivery.objects.select_for_update(skip_locked=True)
                .filter(sendout_id__in=due_ids)
                .filter(
                    status__in=[
                        SendoutDelivery.Status.PENDING,
                        SendoutDelivery.Status.FAILED,
                    ]
                )
                .exclude(
                    status=SendoutDelivery.Status.FAILED,
                    retry_count__gte=max_retries,
                )
                .values_list("id", flat=True)[:BATCH_SIZE]
            )

            if not delivery_ids:
                return iter([])

            SendoutDelivery.objects.filter(id__in=delivery_ids).update(
                status=SendoutDelivery.Status.PROCESSING
            )

        return (
            SendoutDelivery.objects.filter(id__in=delivery_ids)
            .select_related("sendout__newsletter", "subscriber")
            .iterator(chunk_size=BATCH_SIZE)
        )

    def next_task(self) -> SendoutDelivery | None:
        try:
            return next(self._iterator)
        except StopIteration:
            self._iterator = self._fanout_and_get_batch()
            try:
                return next(self._iterator)
            except StopIteration:
                return None
