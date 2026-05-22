from django.urls import path
from django_email_learning.personalised.api.views import (
    FileUploadView,
    AssignmentSubmissionView,
    QuizSubmissionView,
    AmpQuizSubmissionView,
    SubmitCertificateFormView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizSubmissionView.as_view(), name="quiz_submission"),
    path("quiz-amp/", AmpQuizSubmissionView.as_view(), name="quiz_amp_submission"),
    path(
        "assignment/",
        AssignmentSubmissionView.as_view(),
        name="assignment_submission",
    ),
    path(
        "file-upload/",
        FileUploadView.as_view(),
        name="file_upload",
    ),
    path(
        "certificate-form/",
        SubmitCertificateFormView.as_view(),
        name="submit_certificate_form",
    ),
]
