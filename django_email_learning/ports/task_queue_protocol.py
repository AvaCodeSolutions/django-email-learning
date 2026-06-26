from typing import Generic, Protocol, TypeVar

T = TypeVar("T")


class TaskQueueProtocol(Protocol, Generic[T]):
    def next_task(self) -> T | None:
        ...
