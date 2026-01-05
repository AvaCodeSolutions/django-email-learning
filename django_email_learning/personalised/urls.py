from django.urls import path
from django_email_learning.personalised.views import QuizPublicView

app_name = "email_learning"

urlpatterns = [
    path("quiz/", QuizPublicView.as_view(), name="quiz_public_view"),
]
