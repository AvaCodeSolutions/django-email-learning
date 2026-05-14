from unittest.mock import patch

from django_email_learning.models import AssignmentSubmission, ContentDelivery


def test_assignment_submission_save_triggers_next_delivery_on_first_approval_for_blocking_assignment(
    db, course_assignment_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    submission = AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="Initial answer",
    )

    with patch.object(ContentDelivery, "schedule_next_delivery") as mock_schedule:
        submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
        submission.save()

    assert mock_schedule.call_count == 1


def test_assignment_submission_save_does_not_trigger_next_delivery_when_already_approved(
    db, course_assignment_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )

    with patch.object(ContentDelivery, "schedule_next_delivery") as mock_schedule:
        submission = AssignmentSubmission.objects.create(
            delivery=delivery,
            text_submission="Initial answer",
        )
        submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
        submission.save()

        submission.text_submission = "Edited approved answer"
        submission.save()

    assert mock_schedule.call_count == 1


def test_assignment_submission_save_does_not_trigger_next_delivery_for_non_blocking_assignment(
    db, course_assignment_content, enrollment
):
    course_assignment_content.assignment.is_blocking = False
    course_assignment_content.assignment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )

    with patch.object(ContentDelivery, "schedule_next_delivery") as mock_schedule:
        submission = AssignmentSubmission.objects.create(
            delivery=delivery,
            text_submission="Initial answer",
        )
        submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
        submission.save()

    mock_schedule.assert_not_called()
