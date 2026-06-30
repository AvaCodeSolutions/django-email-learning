from pydantic import BaseModel, Field

from .group_enrollment.google_group_enrollment_handler import (
    GoogleGroupEnrollmentHandler,
)


class CreateSessionRequest(BaseModel):
    handler: GoogleGroupEnrollmentHandler = Field(..., discriminator="provider_and_purpose")
