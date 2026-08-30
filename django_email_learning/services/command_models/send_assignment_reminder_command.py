from typing import Literal

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from pydantic import ConfigDict

from django_email_learning.models import ContentDelivery, DeliverySchedule
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email


class AssignmentNotFoundError(Exception):
    pass


class SendAssignmentReminderCommand(AbstractCommand):
    command_name: Literal["send_assignment_reminder"] = "send_assignment_reminder"
    delivery_schedule: DeliverySchedule

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def execute(self) -> None:
        content = self.delivery_schedule.delivery.course_content
        if not content.assignment:
            raise AssignmentNotFoundError(f"CourseContent with ID {content.id} has no associated assignment")
        email = self.delivery_schedule.delivery.enrollment.learner.email
        self.logger.info(
            f"Sending reminder for assignment with ID {content.assignment.id} to email {mask_email(email)}"
        )

        assignment = content.assignment

        subject = _("Reminder: Assignment '{assignment_title}' is due soon").format(assignment_title=assignment.title)
        context = {
            "assignment": assignment,
            "link": self.delivery_schedule.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(email),
            "deadline_time": self.delivery_schedule.delivery.valid_until,
        }
        payload = render_to_string("emails/assignment_reminder.txt", context)

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_sender_service.from_email_for_course(content.course),
            to=[email],
        )
        email_message.attach_alternative(render_to_string("emails/assignment_reminder.html", context), "text/html")

        try:
            email_sender_service.send(email_message)
            self.delivery_schedule.delivery.remind_at = timezone.now()
            self.delivery_schedule.delivery.reminder_state = ContentDelivery.ReminderStatus.SENT
            self.delivery_schedule.delivery.save()
            metric_service.assignment_reminder_sent(
                course_slug=content.course.slug,
                organization_id=content.course.organization.id,
                assignment_id=assignment.id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send assignment reminder for assignment with ID {assignment.id}"
                f" to email {mask_email(email)}: {str(e)}"
            )
            raise e
