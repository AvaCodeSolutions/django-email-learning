from django_email_learning.services.command_models.command_request import CommandRequest
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)
from pydantic import ValidationError


class InvalidCommandError(Exception):
    pass


class CommandHandlerService:
    def handle_command(self, command: EnrollCommand | UnsubscribeCommand) -> None:
        try:
            request = CommandRequest(command=command)
            request.command.execute()
        except ValidationError as e:
            raise InvalidCommandError("Invalid command") from e

    def handle_json_command(self, json_command: dict) -> None:
        try:
            request = CommandRequest.model_validate(json_command)
            request.command.execute()
        except ValidationError as e:
            raise InvalidCommandError("Invalid command JSON") from e
