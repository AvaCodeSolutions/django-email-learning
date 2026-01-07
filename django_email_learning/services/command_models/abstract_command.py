from abc import ABC, abstractmethod
from pydantic import BaseModel
import logging


class AbstractCommand(ABC, BaseModel):
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError("Subclasses must implement the execute method")
