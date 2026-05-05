from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import CourseContent
from django_email_learning.services.email_sender_service import EmailSenderService
from django_email_learning.services.metrics_service import MetricsService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal

from django_email_learning.services.utils import mask_email


class AssignmentNotFoundError(Exception):
    pass


class SendAssignmentCommand(AbstractCommand):
    command_name: Literal["send_assignment"] = "send_assignment"
    link: str
    email: str
    content_id: int

    def execute(self) -> None:
        metric_service = MetricsService()
        content = CourseContent.objects.get(id=self.content_id)
        if not content.assignment:
            raise AssignmentNotFoundError(
                f"CourseContent with ID {self.content_id} has no associated assignment"
            )
        self.logger.info(
            f"Sending assignment with ID {content.assignment.id} to email {mask_email(self.email)}"
        )

        assignment = content.assignment
        subject = assignment.title
        context = {
            "assignment": assignment,
            "link": self.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
        }
        payload = render_to_string("emails/assignment.txt", context)

        email_service = EmailSenderService()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_service.from_email,
            to=[self.email],
        )
        email_message.attach_alternative(
            render_to_string("emails/assignment.html", context), "text/html"
        )

        email_service.send(email_message)
        metric_service.assignment_sent(
            course_slug=content.course.slug,
            organization_id=content.course.organization.id,
            assignment_id=assignment.id,
        )
