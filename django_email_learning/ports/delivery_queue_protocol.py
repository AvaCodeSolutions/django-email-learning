from typing import Protocol
from django_email_learning.models import DeliverySchedule


class DeliveryQueueProtocol(Protocol):
    def next_task(self) -> DeliverySchedule | None:
        ...
