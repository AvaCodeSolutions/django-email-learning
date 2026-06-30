import json
from unittest.mock import patch

from django.urls import reverse
from django_email_learning.models import (
    AssignmentFeedback,
    AssignmentSubmission,
    ContentDelivery,
)
import pytest


def get_url(organization_id: int, course_id: int, submission_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:submission_review",
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
        ("instructor", 200),
        ("editor", 403),
        ("viewer", 403),
        ("anonymous", 401),
    ],
    indirect=["client"],
)
def test_submission_review_role_access(
    client, expected_status, submission, course_assignment_content
):
    response = client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == expected_status


def test_submission_review_updates_status_to_approved(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    submission.refresh_from_db()
    assert submission.status == AssignmentSubmission.SubmissionStatus.APPROVED


def test_submission_review_updates_status_to_rejected(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "rejected"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    submission.refresh_from_db()
    assert submission.status == AssignmentSubmission.SubmissionStatus.REJECTED


def test_submission_review_updates_status_to_requesting_changes(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "requesting_changes"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    submission.refresh_from_db()
    assert submission.status == AssignmentSubmission.SubmissionStatus.REQUESTING_CHANGES


def test_submission_review_creates_feedback_when_provided_by_instructor(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "approved", "comment": "Well done!"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    feedback = AssignmentFeedback.objects.filter(submission=submission).first()
    assert feedback is not None
    assert feedback.comment == "Well done!"


def test_submission_review_does_not_create_feedback_when_not_provided(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "rejected"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert not AssignmentFeedback.objects.filter(submission=submission).exists()


def test_submission_review_returns_404_for_nonexistent_submission(
    org_admin_client, course_assignment_content
):
    response = org_admin_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=99999,
        ),
        data=json.dumps({"review_result": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"error": "Assignment submission not found"}


def test_submission_review_returns_401_when_submission_belongs_to_different_org(
    db, org_admin_client, course_assignment_content
):
    """
    The accessible_for decorator passes for org 1 (where the admin has a role).
    The view's own check then rejects with 401 when the submission belongs to a
    different organization than the one in the URL.
    """
    from django_email_learning.models import (
        Course,
        Enrollment,
        ImapConnection,
        Learner,
        Organization,
    )

    org2 = Organization.objects.create(name="Other Org")
    imap2 = ImapConnection.objects.create(
        server="imap.other.com",
        port=993,
        email="other@example.com",
        password="secret",
        organization=org2,
    )
    course2 = Course.objects.create(
        title="Other Course",
        slug="other-course",
        imap_connection=imap2,
        organization=org2,
    )
    from django_email_learning.models import Assignment, CourseContent

    assignment2 = Assignment.objects.create(
        title="Other Assignment",
        description="desc",
        is_blocking=True,
        deadline_days=7,
        requires_text_submission=True,
        requires_file_submission=False,
    )
    content2 = CourseContent.objects.create(
        course=course2,
        priority=1,
        type="assignment",
        assignment=assignment2,
        waiting_period=3600,
        is_published=True,
    )
    import uuid

    learner2 = Learner.objects.create(
        email=f"{uuid.uuid4().hex}@example.com", organization=org2
    )
    enrollment2 = Enrollment.objects.create(learner=learner2, course=course2)
    delivery2 = ContentDelivery.objects.create(
        enrollment=enrollment2, course_content=content2
    )
    submission2 = AssignmentSubmission.objects.create(
        delivery=delivery2, text_submission="Answer"
    )

    # POST to org 1 (where the admin has access), but submission belongs to org 2
    response = org_admin_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission2.id,
        ),
        data=json.dumps({"review_result": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_submission_review_response_includes_expected_fields(
    instructor_client, submission, course_assignment_content
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "rejected"}),
        content_type="application/json",
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
        "file_submission",
        "text_submission",
        "file_name",
        "learner",
    }
    assert payload["status"] == AssignmentSubmission.SubmissionStatus.REJECTED


@patch(
    "django_email_learning.platform.api.views.assignments.SendAssignmentReviewCommand"
)
def test_submission_review_calls_review_command_when_status_changes(
    mock_send_assignment_review_command,
    instructor_client,
    submission,
    course_assignment_content,
):
    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    mock_send_assignment_review_command.assert_called_once()
    call_kwargs = mock_send_assignment_review_command.call_args.kwargs
    assert call_kwargs["submission"].id == submission.id
    assert call_kwargs["include_last_feedback"] is False
    mock_send_assignment_review_command.return_value.execute.assert_called_once_with()


@patch(
    "django_email_learning.platform.api.views.assignments.SendAssignmentReviewCommand"
)
def test_submission_review_does_not_call_review_command_when_status_unchanged_and_no_comment(
    mock_send_assignment_review_command,
    instructor_client,
    submission,
    course_assignment_content,
):
    submission.status = AssignmentSubmission.SubmissionStatus.REJECTED
    submission.save(update_fields=["status"])

    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps({"review_result": "rejected"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    mock_send_assignment_review_command.assert_not_called()


@patch(
    "django_email_learning.platform.api.views.assignments.SendAssignmentReviewCommand"
)
def test_submission_review_calls_review_command_when_comment_is_provided_even_if_status_unchanged(
    mock_send_assignment_review_command,
    instructor_client,
    submission,
    course_assignment_content,
):
    submission.status = AssignmentSubmission.SubmissionStatus.REJECTED
    submission.save(update_fields=["status"])

    response = instructor_client.post(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
            submission_id=submission.id,
        ),
        data=json.dumps(
            {"review_result": "rejected", "comment": "Needs more details."}
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    mock_send_assignment_review_command.assert_called_once()
    call_kwargs = mock_send_assignment_review_command.call_args.kwargs
    assert call_kwargs["submission"].id == submission.id
    assert call_kwargs["include_last_feedback"] is True
    mock_send_assignment_review_command.return_value.execute.assert_called_once_with()
