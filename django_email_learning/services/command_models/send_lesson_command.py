from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import Lesson, CourseContent
from django_email_learning.services.email_sender_service import EmailSenderService
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal


class LessonNotFoundError(Exception):
    pass


class SendLessonCommand(AbstractCommand):
    command_name: Literal["send_lesson"] = "send_lesson"
    content_id: int
    email: str

    def execute(self) -> None:
        content = CourseContent.objects.get(id=self.content_id)
        if not content.lesson:
            raise LessonNotFoundError(
                f"CourseContent with ID {self.content_id} has no associated lesson"
            )
        self.logger.info(
            f"Sending lesson with ID {content.lesson.id} to email {self.email}"
        )

        try:
            lesson = Lesson.objects.get(id=content.lesson.id)
        except Lesson.DoesNotExist:
            raise LessonNotFoundError(f"Lesson with ID {content.lesson.id} not found")

        subject = lesson.title
        context = {
            "lesson": lesson,
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
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
