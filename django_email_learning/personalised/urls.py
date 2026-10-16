from django.urls import path

from django_email_learning.personalised.views import (
    AssignmentPublicView,
    CertificateFormView,
    CertificateView,
    DecisionPublicView,
    QuizPublicView,
    TrackEnrollmentEmailOpenView,
    TrackOpenView,
    UnsubscribeView,
    VerifyEnrollmentView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizPublicView.as_view(), name="quiz_public_view"),
    path("assignment/", AssignmentPublicView.as_view(), name="assignment_public_view"),
    path("decision/", DecisionPublicView.as_view(), name="decision_public_view"),
    path("verify-enrollment/", VerifyEnrollmentView.as_view(), name="verify_enrollment"),
    path("certificate-form/", CertificateFormView.as_view(), name="certificate_form"),
    path(
        "certificate/<str:certificate_number>/",
        CertificateView.as_view(),
        name="certificate",
    ),
    path("unsubscribe/", UnsubscribeView.as_view(), name="unsubscribe"),
    path("track/open/<str:hash_value>/", TrackOpenView.as_view(), name="track_open"),
    path(
        "track/enrollment-open/<str:token>/",
        TrackEnrollmentEmailOpenView.as_view(),
        name="track_enrollment_email_open",
    ),
    path(
        "track/enrollment-reminder-open/<str:token>/",
        TrackEnrollmentEmailOpenView.as_view(reminder=True),
        name="track_enrollment_reminder_open",
    ),
]
