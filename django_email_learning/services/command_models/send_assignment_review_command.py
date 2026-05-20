from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import AssignmentSubmission
from django_email_learning.services.email_sender_service import EmailSenderService
from django_email_learning.services.metrics_service import MetricsService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal, Optional
from pydantic import ConfigDict
from django.utils.translation import gettext as _
from django_email_learning.services.utils import mask_email


class AssignmentSubmissionNotFoundError(Exception):
    pass


class SendAssignmentReviewCommand(AbstractCommand):
    command_name: Literal["send_assignment_review"] = "send_assignment_review"
    submission: AssignmentSubmission
    include_last_feedback: Optional[bool] = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def execute(self) -> None:
        metric_service = MetricsService()

        if not self.submission.assignment:
            raise AssignmentSubmissionNotFoundError(
                f"CourseContent with ID {self.submission.id} has no associated assignment"
            )

        if self.include_last_feedback:
            feedback = self.submission.feedbacks.order_by("-provided_at").first()
        else:
            feedback = None
        email = self.submission.delivery.enrollment.learner.email
        self.logger.info(
            f"Sending review for assignment with ID {self.submission.assignment.id} to email {mask_email(email)}"
        )

        assignment = self.submission.assignment

        if (
            self.submission.status
            == AssignmentSubmission.SubmissionStatus.REQUESTING_CHANGES
        ):
            subject = _(
                "Update Required: Feedback on your assignment '{assignment_title}'"
            ).format(assignment_title=assignment.title)
            message = _(
                "Your assignment has been reviewed, but changes are required before it can be approved."
            )
            if feedback:
                message += _(
                    " Please see the feedback below for more details and update your submission accordingly."
                )
            else:
                message += _(" Please update your submission.")
            change_requested = True
            title_prefix = _("Change Requested")
        elif self.submission.status == AssignmentSubmission.SubmissionStatus.APPROVED:
            subject = _("Your assignment has been approved").format(
                assignment_title=assignment.title
            )
            message = _("Your assignment has been reviewed and approved. Great job!")
            change_requested = False
            title_prefix = _("Approved")
        elif self.submission.status == AssignmentSubmission.SubmissionStatus.REJECTED:
            subject = _("Your assignment has been rejected").format(
                assignment_title=assignment.title
            )
            message = _("Your assignment has been reviewed and rejected.")
            if feedback:
                message += _(" Please see the feedback below for more details.")
            change_requested = False
            title_prefix = _("Rejected")
        else:
            raise ValueError(f"Invalid submission status: {self.submission.status}")

        course = self.submission.delivery.enrollment.course

        context = {
            "message": message,
            "assignment": assignment,
            "title_prefix": title_prefix,
            "feedback": {
                "provider": {
                    "name": feedback.provided_by.display_name
                    if feedback.provided_by.display_name
                    else _("Instructor"),
                    "photo": feedback.provided_by.photo.url
                    if feedback.provided_by.photo
                    else None,
                }
                if feedback.provided_by
                else None,
                "comment": feedback.comment,
            }
            if feedback
            else None,
            "change_requested": change_requested,
            "link": self.submission.delivery.link,
            "unsubscribe_link": course.generate_unsubscribe_link(email),
        }
        payload = render_to_string("emails/assignment_review.txt", context)

        email_service = EmailSenderService()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_service.from_email,
            to=[email],
        )
        email_message.attach_alternative(
            render_to_string("emails/assignment_review.html", context), "text/html"
        )

        try:
            email_service.send(email_message)
            metric_service.assignment_review_sent(
                course_slug=course.slug,
                organization_id=course.organization.id,
                assignment_id=assignment.id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send assignment review for assignment with ID {assignment.id} to email {mask_email(email)}: {str(e)}"
            )
            raise e
