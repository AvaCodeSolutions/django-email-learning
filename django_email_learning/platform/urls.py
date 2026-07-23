from django.urls import path

from django_email_learning.platform.views import (
    Analytics,
    ApiKeys,
    Courses,
    CourseView,
    Dashboard,
    Learners,
    NewsletterDetailView,
    NewsletterSubscribersView,
    Organizations,
    PrivateFileView,
    SingleOrganization,
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
    path(
        "organizations/<int:organization_id>/newsletters/<int:newsletter_id>/",
        NewsletterDetailView.as_view(),
        name="newsletter_detail_view",
    ),
    path(
        "organizations/<int:organization_id>/newsletters/<int:newsletter_id>/subscribers/",
        NewsletterSubscribersView.as_view(),
        name="newsletter_subscribers_view",
    ),
    path("private_file/", PrivateFileView.as_view(), name="private_file_view"),
    path("learners/", Learners.as_view(), name="learners_view"),
    path("settings/api_keys/", ApiKeys.as_view(), name="api_keys_view"),
    path("analytics/", Analytics.as_view(), name="analytics_view"),
    path("", Dashboard.as_view(), name="root"),
]
