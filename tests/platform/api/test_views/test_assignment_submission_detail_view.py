import pytest
from django.urls import reverse

from django_email_learning.models import (
    Assignment,
    AssignmentFeedback,
    AssignmentSubmission,
    ContentDelivery,
    Course,
    CourseContent,
    CourseContentType,
    Enrollment,
    Learner,
    Organization,
    OrganizationUser,
)


def get_url(organization_id: int, course_id: int, submission_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:submitted_assignments_detail",
        kwargs={
            "organization_id": organization_id,
            "course_id": course_id,
            "submission_id": submission_id,
        },
    )


@pytest.fixture()
def submission(enrollment, course_assignment_content):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    return AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="My answer",
    )


@pytest.mark.parametrize(
    "client,expected_status",
    [
        ("org_admin", 200),
        ("instructor", 200),
        ("editor", 403),
        ("viewer", 403),
        ("anonymous", 401),
    ],
    indirect=["client"],
)
def test_assignment_submission_detail_view_role_access(client, expected_status, submission, course_assignment_content):
    response = client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        )
    )

    assert response.status_code == expected_status


def test_assignment_submission_detail_view_returns_expected_fields(
    org_admin_client, submission, course_assignment_content
):
    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "id",
        "assignment_title",
        "submitted_at",
        "status",
        "reviewed_at",
        "reviewed_by",
        "feedbacks",
        "text_submission",
        "file_submission",
        "file_name",
        "learner",
    }
    assert payload["id"] == submission.id
    assert payload["assignment_title"] == course_assignment_content.assignment.title
    assert payload["status"] == AssignmentSubmission.SubmissionStatus.PENDING_REVIEW
    assert payload["reviewed_at"] is None
    assert payload["reviewed_by"] is None
    assert payload["feedbacks"] == []


def test_assignment_submission_detail_view_returns_404_for_nonexistent_submission(
    org_admin_client, course_assignment_content
):
    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=99999,
        )
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Assignment submission not found"}


def test_assignment_submission_detail_view_includes_reviewer_info(
    org_admin_client, users, submission, course_assignment_content
):
    reviewer = OrganizationUser.objects.get(user=users["instructor_user"], organization_id=1)
    submission.reviewer = reviewer
    submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
    submission.save()

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == AssignmentSubmission.SubmissionStatus.APPROVED
    assert payload["reviewed_by"] is not None
    assert payload["reviewed_by"]["display_name"] == reviewer.display_name


def test_assignment_submission_detail_view_cross_organization_returns_404(org_admin_client):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        description="Belongs to a different organization.",
        organization=other_org,
    )
    other_assignment = Assignment.objects.create(
        title="Other Org Assignment",
        description="desc",
        is_blocking=True,
        deadline_days=7,
        requires_text_submission=True,
        requires_file_submission=False,
    )
    other_content = CourseContent.objects.create(
        course=other_course,
        priority=1,
        type=CourseContentType.ASSIGNMENT,
        assignment=other_assignment,
        waiting_period=0,
    )
    other_learner = Learner.objects.create(email="other-org-learner@example.com", organization=other_org)
    other_enrollment = Enrollment.objects.create(learner=other_learner, course=other_course)
    other_delivery = ContentDelivery.objects.create(enrollment=other_enrollment, course_content=other_content)
    other_submission = AssignmentSubmission.objects.create(delivery=other_delivery, text_submission="Secret answer")

    response = org_admin_client.get(
        get_url(
            organization_id=1,
            course_id=other_course.id,
            submission_id=other_submission.id,
        )
    )

    assert response.status_code == 404


def test_assignment_submission_detail_view_includes_feedbacks(
    org_admin_client, users, submission, course_assignment_content
):
    provider = OrganizationUser.objects.get(user=users["instructor_user"], organization_id=1)
    AssignmentFeedback.objects.create(
        submission=submission,
        comment="Good work!",
        provided_by=provider,
    )

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        )
    )

    assert response.status_code == 200
    feedbacks = response.json()["feedbacks"]
    assert len(feedbacks) == 1
    assert feedbacks[0]["provided_by"]["display_name"] == provider.display_name
