from typing import Literal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from django_email_learning.models import CourseContent
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.email_buttons import link_variables, render_as_text, render_buttons
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.utils import mask_email


class GateNotFoundError(Exception):
    pass


class SendGateCommand(AbstractCommand):
    """Emails a gate's message to a learner who has just reached it."""

    command_name: Literal["send_gate"] = "send_gate"
    content_id: int
    enrollment_id: int
    email: str

    def execute(self) -> None:
        conf = settings.DJANGO_EMAIL_LEARNING
        content = CourseContent.objects.get(id=self.content_id)
        if not content.gate:
            raise GateNotFoundError(f"CourseContent with ID {self.content_id} has no associated gate")
        gate = content.gate
        self.logger.info(f"Sending gate message for gate ID {gate.id} to email {mask_email(self.email)}")

        delivery = content.contentdelivery_set.filter(enrollment_id=self.enrollment_id).first()
        track_open_url = (
            f"{conf['SITE_BASE_URL']}"
            f"{reverse('django_email_learning:personalised:track_open', kwargs={'hash_value': delivery.hash_value})}"
            if delivery
            else None
        )
        button_values = link_variables(enrollment_id=self.enrollment_id, email=self.email)
        context = {
            "gate": gate,
            "message": render_buttons(gate.message, button_values, content.course.organization.brand_color),
            "message_text": render_as_text(gate.message, button_values),
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
            "track_open_url": track_open_url,
            **email_sender_service.organization_footer_context(content.course),
        }
        email_message = EmailMultiAlternatives(
            subject=gate.title,
            body=render_to_string("emails/gate.txt", context),
            from_email=email_sender_service.from_email_for_course(content.course),
            to=[self.email],
        )
        email_message.attach_alternative(render_to_string("emails/gate.html", context), "text/html")
        email_sender_service.send(email_message)
