from django.urls import path

from django_email_learning.personalised.views import (
    AssignmentPublicView,
    CertificateDownloadView,
    CertificateFormView,
    CertificateView,
    QuizPublicView,
    TrackOpenView,
    UnsubscribeView,
    VerifyEnrollmentView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizPublicView.as_view(), name="quiz_public_view"),
    path("assignment/", AssignmentPublicView.as_view(), name="assignment_public_view"),
    path("verify-enrollment/", VerifyEnrollmentView.as_view(), name="verify_enrollment"),
    path("certificate-form/", CertificateFormView.as_view(), name="certificate_form"),
    path(
        "certificate/<str:certificate_number>/",
        CertificateView.as_view(),
        name="certificate",
    ),
    path(
        "certificate/<str:certificate_number>/download/",
        CertificateDownloadView.as_view(),
        name="certificate_download",
    ),
    path("unsubscribe/", UnsubscribeView.as_view(), name="unsubscribe"),
    path("track/open/<str:hash_value>/", TrackOpenView.as_view(), name="track_open"),
]
