import logging
from typing import Iterator

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from django_email_learning.models import NewsletterSubscriber, Sendout, SendoutDelivery
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


def get_max_retries() -> int:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return int(conf.get("NEWSLETTERS", {}).get("MAX_RETRIES", 3))


def is_sendout_allowed(sendout: Sendout) -> bool:
    """
    Returns whether the given due sendout is allowed to be sent.

    Reads DJANGO_EMAIL_LEARNING["NEWSLETTERS"]["SENDOUT_ALLOWED_RESOLVER"], a dotted
    path to a callable(sendout: Sendout) -> bool. Defaults to always-allowed when unset,
    letting library users implement custom logic (e.g. a cap on sendouts per period)
    without forking the sending job.
    """
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    resolver_path = conf.get("NEWSLETTERS", {}).get("SENDOUT_ALLOWED_RESOLVER")
    if resolver_path:
        resolver = import_string(resolver_path)
        return bool(resolver(sendout))
    return True


class DatabaseSendoutQueue(TaskQueueProtocol[SendoutDelivery]):
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

        # Step 1.5: filter out sendouts the configured resolver denies. A due sendout is
        # checked individually (not cached per organization) since one sendout's outcome
        # can change what should happen for the next one from the same organization. A
        # denial is treated as permanent — a retry loop rarely helps here (a cap that's
        # already hit this poll will likely still be hit on the next one moments later)
        # — so the sendout is immediately moved to BLOCKED instead of staying SCHEDULED.
        allowed_ids: list[int] = []
        for due_sendout in Sendout.objects.filter(id__in=due_ids).select_related("newsletter__organization"):
            if is_sendout_allowed(due_sendout):
                allowed_ids.append(due_sendout.id)
                continue

            due_sendout.status = Sendout.Status.BLOCKED
            due_sendout.blocked_reason = Sendout.BlockedReason.DENIED_BY_RESOLVER
            due_sendout.save(update_fields=["status", "blocked_reason"])
            logger.warning(f"Sendout {due_sendout.id}: blocked by SENDOUT_ALLOWED_RESOLVER.")
            metric_service.sendout_blocked_by_resolver(
                sendout_id=due_sendout.id,
                newsletter_id=due_sendout.newsletter_id,
            )

        due_ids = allowed_ids
        if not due_ids:
            return iter([])

        # Step 2: lazy fan-out — create a SendoutDelivery for every current,
        # confirmed subscriber that doesn't already have one (idempotent via
        # ignore_conflicts). Unconfirmed subscribers are excluded entirely -
        # if they confirm later, they'll be picked up by a future sendout's
        # own fan-out.
        for sendout_id in due_ids:
            subscriber_ids = list(
                NewsletterSubscriber.objects.filter(
                    newsletter__sendouts__id=sendout_id, confirmed_at__isnull=False
                ).values_list("id", flat=True)
            )
            if subscriber_ids:
                SendoutDelivery.objects.bulk_create(
                    [SendoutDelivery(sendout_id=sendout_id, subscriber_id=sid) for sid in subscriber_ids],
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

            SendoutDelivery.objects.filter(id__in=delivery_ids).update(status=SendoutDelivery.Status.PROCESSING)

        return (
            SendoutDelivery.objects.filter(id__in=delivery_ids)
            .select_related("sendout__newsletter__organization", "subscriber")
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
