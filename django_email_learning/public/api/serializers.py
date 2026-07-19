import re
from typing import List

from pydantic import BaseModel, Field, field_validator


class EmailValidatedRequest(BaseModel):
    email: str

    @field_validator("email")
    def validate_email(cls, v: str) -> str:
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v


class EnrollmentRequest(EmailValidatedRequest):
    organization_id: int
    course_slug: str = Field(min_length=1)
    subscribe_to_newsletter: bool = False


class EmbeddableEnrollmentRequest(EmailValidatedRequest):
    """Same as EnrollmentRequest but without organization_id: the embed API
    resolves the organization from the embed_token in the URL instead of
    trusting a caller-supplied id.
    """

    course_slug: str = Field(min_length=1)
    subscribe_to_newsletter: bool = False


class NewsletterSubscribeRequest(EmailValidatedRequest):
    newsletter_ids: List[int] = Field(min_length=1)
