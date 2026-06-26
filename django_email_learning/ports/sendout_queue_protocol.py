from typing import Protocol

from django_email_learning.models import SendoutDelivery


class SendoutQueueProtocol(Protocol):
    def next_task(self) -> SendoutDelivery | None:
        ...
