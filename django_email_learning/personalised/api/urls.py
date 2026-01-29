from django.urls import path
from django_email_learning.personalised.api.views import QuizSubmissionView

app_name = "django_email_learning"

urlpatterns = [
    path("quiz/", QuizSubmissionView.as_view(), name="quiz_submission"),
]
