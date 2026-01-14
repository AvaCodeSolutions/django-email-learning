from pydantic import BaseModel, Field, field_validator
import re


class EnrollmentRequest(BaseModel):
    organization_id: int
    email: str
    course_slug: str = Field(min_length=1)

    @field_validator("email")
    def validate_email(cls, v: str) -> str:
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v
