from django.urls import path
from django_email_learning.public.api.views import EnrollView

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollView.as_view(), name="enroll"),
]
