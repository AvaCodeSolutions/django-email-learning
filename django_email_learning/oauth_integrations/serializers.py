from pydantic import BaseModel

from django_email_learning.services.command_models.command_request import CommandRequest


class CreateSessionRequest(BaseModel):
    request: CommandRequest
