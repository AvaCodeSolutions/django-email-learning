from django.urls import path
from django.views.defaults import page_not_found
from django_email_learning.platform.api.views import (
    ApiKeyView,
    SingleApiKeyView,
    CourseView,
    EnrollmentView,
    EnrollmentsStatisticsView,
    FileView,
    ImapConnectionView,
    OrganizationsView,
    SingleOrganizationView,
    SingleCourseView,
    CourseContentView,
    ReorderCourseContentView,
    SingleCourseContentView,
    UpdateSessionView,
    LearnersView,
    SingleLearnerView,
    JobsStatus,
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
    path(
        "organizations/<int:organization_id>/courses/<int:course_id>/contents/",
        CourseContentView.as_view(),
        name="course_content_view",
    ),
    path(
        "organizations/<int:organization_id>/courses/<int:course_id>/contents/reorder/",
        ReorderCourseContentView.as_view(),
        name="reorder_course_contents_view",
    ),
    path(
        "organizations/<int:organization_id>/courses/<int:course_id>/contents/<int:course_content_id>/",
        SingleCourseContentView.as_view(),
        name="single_course_content_view",
    ),
    path(
        "organizations/<int:organization_id>/learners/",
        LearnersView.as_view(),
        name="learners_view",
    ),
    path(
        "organizations/<int:organization_id>/learners/<int:learner_id>/",
        SingleLearnerView.as_view(),
        name="single_learner_view",
    ),
    path(
        "organizations/<int:organization_id>/enrollments/<int:enrollment_id>/",
        EnrollmentView.as_view(),
        name="enrollment_view",
    ),
    path(
        "organizations/<int:organization_id>/courses/<int:course_id>/enrollments/statistics/",
        EnrollmentsStatisticsView.as_view(),
        name="enrollments_statistics_view",
    ),
    path(
        "organizations/<int:organization_id>/file/",
        FileView.as_view(),
        name="file_view",
    ),
    path("organizations/", OrganizationsView.as_view(), name="organizations_view"),
    path(
        "organizations/<int:organization_id>/",
        SingleOrganizationView.as_view(),
        name="single_organization_view",
    ),
    path("status/jobs/", JobsStatus.as_view(), name="jobs_status_view"),
    path("api_keys/", ApiKeyView.as_view(), name="api_key_view"),
    path(
        "api_keys/<int:api_key_id>/",
        SingleApiKeyView.as_view(),
        name="single_api_key_view",
    ),
    path("session", UpdateSessionView.as_view(), name="update_session_view"),
    path("", page_not_found, name="root"),
]
