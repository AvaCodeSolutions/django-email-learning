from typing import Literal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from django_email_learning.models import CourseContent
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.utils import mask_email


class DecisionNotFoundError(Exception):
    pass


class SendDecisionCommand(AbstractCommand):
    command_name: Literal["send_decision"] = "send_decision"
    link: str
    email: str
    content_id: int

    def execute(self) -> None:
        conf = settings.DJANGO_EMAIL_LEARNING
        content = CourseContent.objects.get(id=self.content_id)
        if not content.decision:
            raise DecisionNotFoundError(f"CourseContent with ID {self.content_id} has no associated decision")
        decision = content.decision
        self.logger.info(f"Sending decision with ID {decision.id} to email {mask_email(self.email)}")

        delivery = content.contentdelivery_set.filter(enrollment__learner__email=self.email).first()
        track_open_url = (
            f"{conf['SITE_BASE_URL']}"
            f"{reverse('django_email_learning:personalised:track_open', kwargs={'hash_value': delivery.hash_value})}"
            if delivery
            else None
        )
        context = {
            "decision": decision,
            "link": self.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
            "track_open_url": track_open_url,
            **email_sender_service.organization_footer_context(content.course),
        }
        email_message = EmailMultiAlternatives(
            subject=decision.title,
            body=render_to_string("emails/decision.txt", context),
            from_email=email_sender_service.from_email_for_course(content.course),
            to=[self.email],
        )
        email_message.attach_alternative(render_to_string("emails/decision.html", context), "text/html")
        email_sender_service.send(email_message)
