from typing import Protocol


class JobExecutorProtocol(Protocol):
    def submit(self, job_name: str, job_execution_id: int) -> None: ...
