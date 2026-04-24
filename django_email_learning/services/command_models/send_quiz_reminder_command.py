from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import ContentDelivery, DeliverySchedule
from django_email_learning.services.email_sender_service import EmailSenderService
from django_email_learning.services.metrics_service import MetricsService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal
from pydantic import ConfigDict
from django.utils.translation import gettext as _
from django.utils import timezone
from django_email_learning.services.utils import mask_email


class QuizNotFoundError(Exception):
    pass


class SendQuizReminderCommand(AbstractCommand):
    command_name: Literal["send_quiz_reminder"] = "send_quiz_reminder"
    delivery_schedule: DeliverySchedule

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def execute(self) -> None:
        metric_service = MetricsService()
        content = self.delivery_schedule.delivery.course_content
        if not content.quiz:
            raise QuizNotFoundError(
                f"CourseContent with ID {content.id} has no associated quiz"
            )
        email = self.delivery_schedule.delivery.enrollment.learner.email
        self.logger.info(
            f"Sending reminder for quiz with ID {content.quiz.id} to email {mask_email(email)}"
        )

        quiz = content.quiz

        subject = _("Reminder: Quiz '{quiz_title}' is due soon").format(
            quiz_title=quiz.title
        )
        context = {
            "quiz": quiz,
            "link": self.delivery_schedule.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(email),
            "deadline_time": self.delivery_schedule.delivery.valid_until,
        }
        payload = render_to_string("emails/quiz_reminder.txt", context)

        email_service = EmailSenderService()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_service.from_email,
            to=[email],
        )
        email_message.attach_alternative(
            render_to_string("emails/quiz_reminder.html", context), "text/html"
        )

        try:
            email_service.send(email_message)
            self.delivery_schedule.delivery.remind_at = timezone.now()
            self.delivery_schedule.delivery.reminder_state = (
                ContentDelivery.ReminderStatus.SENT
            )
            self.delivery_schedule.delivery.save()
            metric_service.quiz_reminder_sent(
                course_slug=content.course.slug,
                organization_id=content.course.organization.id,
                quiz_id=quiz.id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send quiz reminder for quiz with ID {quiz.id} to email {mask_email(email)}: {str(e)}"
            )
            raise e
