from django.urls import path
from django.views.generic import RedirectView
from django_email_learning.platform.views import Courses, Organizations

app_name = "email_learning"

urlpatterns = [
    path("courses/", Courses.as_view(), name="courses_view"),
    path("organizations/", Organizations.as_view(), name="organizations_view"),
    path(
        "",
        RedirectView.as_view(pattern_name="email_learning:platform:courses_view"),
        name="root",
    ),
]
