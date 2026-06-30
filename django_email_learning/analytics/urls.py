from django.urls import path

from django_email_learning.analytics.views import (
    AverageProgressView,
    CompletionFunnelView,
    DownloadCompletionSummaryView,
    DownloadDeliveryLogView,
    DownloadLearnerProgressView,
    EmailDeliveryOverTimeView,
    EmailDeliveryStatusBreakdownView,
    EmailOpenRateView,
    EnrollmentsOverTimeView,
    EnrollmentStatusBreakdownView,
    TimeToCompleteView,
)

app_name = "django_email_learning"

BASE = "organizations/<int:organization_id>/"

urlpatterns = [
    path(
        f"{BASE}enrollments/over-time/",
        EnrollmentsOverTimeView.as_view(),
        name="enrollments_over_time",
    ),
    path(
        f"{BASE}enrollments/status-breakdown/",
        EnrollmentStatusBreakdownView.as_view(),
        name="enrollments_status_breakdown",
    ),
    path(
        f"{BASE}completion-funnel/",
        CompletionFunnelView.as_view(),
        name="completion_funnel",
    ),
    path(
        f"{BASE}progress/",
        AverageProgressView.as_view(),
        name="average_progress",
    ),
    path(
        f"{BASE}time-to-complete/",
        TimeToCompleteView.as_view(),
        name="time_to_complete",
    ),
    path(
        f"{BASE}email-delivery/over-time/",
        EmailDeliveryOverTimeView.as_view(),
        name="email_delivery_over_time",
    ),
    path(
        f"{BASE}email-delivery/status-breakdown/",
        EmailDeliveryStatusBreakdownView.as_view(),
        name="email_delivery_status_breakdown",
    ),
    path(
        f"{BASE}email-open-rate/",
        EmailOpenRateView.as_view(),
        name="email_open_rate",
    ),
    path(
        f"{BASE}downloads/learner-progress/",
        DownloadLearnerProgressView.as_view(),
        name="download_learner_progress",
    ),
    path(
        f"{BASE}downloads/delivery-log/",
        DownloadDeliveryLogView.as_view(),
        name="download_delivery_log",
    ),
    path(
        f"{BASE}downloads/completion-summary/",
        DownloadCompletionSummaryView.as_view(),
        name="download_completion_summary",
    ),
]
