from typing import Generic, Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class TaskQueueProtocol(Protocol, Generic[T_co]):
    def next_task(self) -> T_co | None: ...
