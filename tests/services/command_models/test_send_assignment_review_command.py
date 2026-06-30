from django.core import mail

from django_email_learning.models import AssignmentSubmission, ContentDelivery
from django_email_learning.services.command_models.send_assignment_review_command import (
    SendAssignmentReviewCommand,
)


def test_send_assignment_review_command_sends_email(db, enrollment, course_assignment_content):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    delivery.delivery_schedules.create(
        time=delivery.enrollment.enrolled_at,
        status="delivered",
        link="https://example.com/assignment/1",
    )

    submission = AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="My answer",
    )
    submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
    submission.save(update_fields=["status"])

    command = SendAssignmentReviewCommand(submission=submission)
    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == "Your assignment has been approved"
    assert enrollment.learner.email in email.to
    assert "Your assignment has been reviewed and approved. Great job!" in email.body
    assert len(email.alternatives) == 1
