from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import Lesson
from django_email_learning.services.email_sender_service import EmailSenderService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal


class LessonNotFoundError(Exception):
    pass


class SendLessonCommand(AbstractCommand):
    command_name: Literal["send_lesson"] = "send_lesson"
    lesson_id: int
    email: str

    def execute(self) -> None:
        self.logger.info(
            f"Sending lesson with ID {self.lesson_id} to email {self.email}"
        )

        try:
            lesson = Lesson.objects.get(id=self.lesson_id)
        except Lesson.DoesNotExist:
            raise LessonNotFoundError(f"Lesson with ID {self.lesson_id} not found")

        subject = lesson.title
        context = {
            "lesson": lesson,
        }
        payload = render_to_string("emails/lesson.txt", context)

        email_service = EmailSenderService()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_service.from_email,
            to=[self.email],
        )
        email_message.attach_alternative(
            render_to_string("emails/lesson.html", context), "text/html"
        )

        email_service.send(email_message)
