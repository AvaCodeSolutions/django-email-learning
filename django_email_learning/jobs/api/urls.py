from django.urls import path

from django_email_learning.jobs.api.views import (
    CheckIMAPJobView,
    CleanupJobExecutionsView,
    DeactivateInactiveEnrollmentsJobView,
    DeliverContentsJobView,
    JobExecutionStatusView,
    SendNewslettersJobView,
    SendQuizRemindersJobView,
)

app_name = "django_email_learning"

urlpatterns = [
    path(
        "deliver_contents/",
        DeliverContentsJobView.as_view(),
        name="deliver_contents",
    ),
    path(
        "check_imap_connections/",
        CheckIMAPJobView.as_view(),
        name="check_imap_connections",
    ),
    path(
        "send_newsletters/",
        SendNewslettersJobView.as_view(),
        name="send_newsletters",
    ),
    path(
        "send_quiz_reminders/",
        SendQuizRemindersJobView.as_view(),
        name="send_quiz_reminders",
    ),
    path(
        "deactivate_inactive_enrollments/",
        DeactivateInactiveEnrollmentsJobView.as_view(),
        name="deactivate_inactive_enrollments",
    ),
    path(
        "cleanup_job_executions/",
        CleanupJobExecutionsView.as_view(),
        name="cleanup_job_executions",
    ),
    path(
        "executions/<int:job_execution_id>/",
        JobExecutionStatusView.as_view(),
        name="job_execution_status",
    ),
]
