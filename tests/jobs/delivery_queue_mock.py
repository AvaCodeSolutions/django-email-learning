from django_email_learning.ports.delivery_queue_protocol import DeliveryQueueProtocol
from django_email_learning.models import DeliverySchedule


class DeliveryQueueMock(DeliveryQueueProtocol):
    def __init__(self) -> None:
        self.tasks = []
        self.index = 0

    def add_task(self, delivery_schedule: DeliverySchedule) -> None:
        self.tasks.append(delivery_schedule)

    def next_task(self):
        if self.index < len(self.tasks):
            task = self.tasks[self.index]
            self.index += 1
            return task
        return None
