from django.urls import path
from django_email_learning.public.api.views import EnrollView

app_name = "django_email_learning"

urlpatterns = [
    path("enroll/", EnrollView.as_view(), name="enroll"),
]
