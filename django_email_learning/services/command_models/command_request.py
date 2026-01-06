from pydantic import BaseModel, Field
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)


class CommandRequest(BaseModel):
    command: EnrollCommand | UnsubscribeCommand = Field(
        ..., discriminator="command_name"
    )
