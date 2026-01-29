from django.urls import path
from django_email_learning.personalised.views import (
    QuizPublicView,
    VerifyEnrollmentView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizPublicView.as_view(), name="quiz_public_view"),
    path(
        "verify-enrollment/", VerifyEnrollmentView.as_view(), name="verify_enrollment"
    ),
]
