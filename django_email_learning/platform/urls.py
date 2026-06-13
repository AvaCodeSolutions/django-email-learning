from django.urls import path
from django.views.generic import RedirectView
from django_email_learning.platform.views import (
    Analytics,
    CourseView,
    Courses,
    Organizations,
    SingleOrganization,
    PrivateFileView,
    Learners,
    ApiKeys,
)

app_name = "django_email_learning"

urlpatterns = [
    path("courses/", Courses.as_view(), name="courses_view"),
    path("courses/<int:course_id>/", CourseView.as_view(), name="course_detail_view"),
    path("organizations/", Organizations.as_view(), name="organizations_view"),
    path(
        "organizations/<int:organization_id>/",
        SingleOrganization.as_view(),
        name="organization_detail_view",
    ),
    path("private_file/", PrivateFileView.as_view(), name="private_file_view"),
    path("learners/", Learners.as_view(), name="learners_view"),
    path("settings/api_keys/", ApiKeys.as_view(), name="api_keys_view"),
    path("analytics/", Analytics.as_view(), name="analytics_view"),
    path(
        "",
        RedirectView.as_view(
            pattern_name="django_email_learning:platform:courses_view"
        ),
        name="root",
    ),
]
