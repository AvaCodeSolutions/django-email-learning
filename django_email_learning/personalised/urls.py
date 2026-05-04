from django.urls import path
from django_email_learning.personalised.views import (
    QuizPublicView,
    AssignmentPublicView,
    VerifyEnrollmentView,
    CertificateFormView,
    CertificateView,
    UnsubscribeView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizPublicView.as_view(), name="quiz_public_view"),
    path("assignment/", AssignmentPublicView.as_view(), name="assignment_public_view"),
    path(
        "verify-enrollment/", VerifyEnrollmentView.as_view(), name="verify_enrollment"
    ),
    path("certificate-form/", CertificateFormView.as_view(), name="certificate_form"),
    path(
        "certificate/<str:certificate_number>/",
        CertificateView.as_view(),
        name="certificate",
    ),
    path("unsubscribe/", UnsubscribeView.as_view(), name="unsubscribe"),
]
