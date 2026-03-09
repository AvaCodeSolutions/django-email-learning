from pydantic import BaseModel, Field
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)
from django_email_learning.services.command_models.enroll_from_google_directory_command import (
    EnrollFromGoogleDirectoryCommand,
)


class CommandRequest(BaseModel):
    command: EnrollCommand | UnsubscribeCommand | EnrollFromGoogleDirectoryCommand = (
        Field(..., discriminator="command_name")
    )
