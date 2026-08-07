from django.urls import path

from django_email_learning.organization_api.views import CoursesView, EnrollmentsView

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollmentsView.as_view(), name="enrollments"),
    path("courses/", CoursesView.as_view(), name="courses"),
]
