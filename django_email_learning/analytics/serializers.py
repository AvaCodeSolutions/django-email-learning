from typing import Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class PeriodCount(BaseModel):
    period: str
    count: int


class CourseStatusCount(BaseModel):
    course_id: int
    course_title: str
    status: str
    count: int


# ---------------------------------------------------------------------------
# Chart responses
# ---------------------------------------------------------------------------


class EnrollmentsOverTimeResponse(BaseModel):
    data: list[PeriodCount]


class EnrollmentStatusBreakdownResponse(BaseModel):
    data: list[CourseStatusCount]


class CompletionFunnelItem(BaseModel):
    course_content_id: int
    course_id: int
    course_title: str
    title: str
    priority: int
    type: str
    learners_reached: int


class CompletionFunnelResponse(BaseModel):
    data: list[CompletionFunnelItem]


class AverageProgressItem(BaseModel):
    course_id: int
    course_title: str
    average_progress: float
    active_enrollments: int


class AverageProgressResponse(BaseModel):
    data: list[AverageProgressItem]


class TimeToCompleteItem(BaseModel):
    course_id: int
    course_title: str
    completion_days: list[float]
    average_days: Optional[float]
    total_completions: int


class TimeToCompleteResponse(BaseModel):
    data: list[TimeToCompleteItem]


class EmailDeliveryOverTimeResponse(BaseModel):
    data: list[PeriodCount]


class EmailDeliveryStatusBreakdownResponse(BaseModel):
    data: list[CourseStatusCount]


class EmailOpenRateItem(BaseModel):
    course_id: int
    course_title: str
    total_delivered: int
    total_opened: int
    open_rate: float


class EmailOpenRateResponse(BaseModel):
    data: list[EmailOpenRateItem]
