from django.urls import path
from django.views.defaults import page_not_found
from django_email_learning.api.views import (
    CourseView,
    ImapConnectionView,
    OrganizationsView,
    SingleCourseView,
    UpdateSessionView,
)

app_name = "django_email_learning"

urlpatterns = [
    path(
        "organizations/<int:organization_id>/courses/",
        CourseView.as_view(),
        name="course_view",
    ),
    path(
        "organizations/<int:organization_id>/imap-connections/",
        ImapConnectionView.as_view(),
        name="imap_connection_view",
    ),
    path(
        "organizations/<int:organization_id>/courses/<int:course_id>/",
        SingleCourseView.as_view(),
        name="single_course_view",
    ),
    path("organizations/", OrganizationsView.as_view(), name="organizations_view"),
    path("session", UpdateSessionView.as_view(), name="update_session_view"),
    path("", page_not_found, name="root"),
]
