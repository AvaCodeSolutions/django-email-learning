from typing import Protocol

from django_email_learning.models import Sendout


class SendoutQueueProtocol(Protocol):
    def next_task(self) -> Sendout | None:
        ...
