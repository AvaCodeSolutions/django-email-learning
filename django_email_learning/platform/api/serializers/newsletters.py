from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsletterResponse(BaseModel):
    id: int
    title: str
    language: str
    organization_id: int
    subscriber_count: int

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_django_model(newsletter: Any) -> "NewsletterResponse":
        return NewsletterResponse(
            id=newsletter.id,
            title=newsletter.title,
            language=newsletter.language,
            organization_id=newsletter.organization_id,
            subscriber_count=newsletter.subscribers.count(),
        )


class CreateNewsletterRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=10)

    def to_django_model(self, organization_id: int) -> Any:
        from django_email_learning.models import Newsletter

        return Newsletter(
            title=self.title,
            language=self.language,
            organization_id=organization_id,
        )


class SendoutResponse(BaseModel):
    id: int
    subject: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class CreateSendoutRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    scheduled_at: datetime


class UpdateSendoutRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    scheduled_at: datetime


class SendoutDetailResponse(BaseModel):
    id: int
    subject: str
    body: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class NewsletterSubscriberResponse(BaseModel):
    id: int
    email: str
    subscribed_at: datetime

    model_config = ConfigDict(from_attributes=True)
