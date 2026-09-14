from typing import Literal

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from pydantic import ConfigDict

from django_email_learning.models import DeliverySchedule
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.send_decision_command import DecisionNotFoundError
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.utils import mask_email


class SendDecisionReminderCommand(AbstractCommand):
    command_name: Literal["send_decision_reminder"] = "send_decision_reminder"
    delivery_schedule: DeliverySchedule

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def execute(self) -> None:
        content = self.delivery_schedule.delivery.course_content
        if not content.decision:
            raise DecisionNotFoundError(f"CourseContent with ID {content.id} has no associated decision")
        decision = content.decision
        email = self.delivery_schedule.delivery.enrollment.learner.email
        self.logger.info(f"Sending reminder for decision with ID {decision.id} to email {mask_email(email)}")

        context = {
            "decision": decision,
            "link": self.delivery_schedule.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(email),
            "deadline_time": self.delivery_schedule.delivery.valid_until,
            **email_sender_service.organization_footer_context(content.course),
        }
        email_message = EmailMultiAlternatives(
            subject=_("Reminder: {decision_title}").format(decision_title=decision.title),
            body=render_to_string("emails/decision_reminder.txt", context),
            from_email=email_sender_service.from_email_for_course(content.course),
            to=[email],
        )
        email_message.attach_alternative(render_to_string("emails/decision_reminder.html", context), "text/html")

        try:
            email_sender_service.send(email_message)
            self.delivery_schedule.delivery.record_reminder_sent()
        except Exception as e:
            self.logger.error(
                f"Failed to send reminder for decision with ID {decision.id} to email {mask_email(email)}: {str(e)}"
            )
            raise e
