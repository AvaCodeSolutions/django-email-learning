from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.models import CourseContent
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from typing import Literal

from django_email_learning.services.utils import mask_email


class QuizNotFoundError(Exception):
    pass


class SendQuizCommand(AbstractCommand):
    command_name: Literal["send_quiz"] = "send_quiz"
    link: str
    email: str
    content_id: int

    def execute(self) -> None:
        content = CourseContent.objects.get(id=self.content_id)
        if not content.quiz:
            raise QuizNotFoundError(
                f"CourseContent with ID {self.content_id} has no associated quiz"
            )
        self.logger.info(
            f"Sending quiz with ID {content.quiz.id} to email {mask_email(self.email)}"
        )

        quiz = content.quiz
        subject = quiz.title
        context = {
            "quiz": quiz,
            "link": self.link,
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
        }
        payload = render_to_string("emails/quiz.txt", context)

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_sender_service.from_email,
            to=[self.email],
        )
        email_message.attach_alternative(
            render_to_string("emails/quiz.html", context), "text/html"
        )

        email_sender_service.send(email_message)
        metric_service.quiz_sent(
            course_slug=content.course.slug,
            organization_id=content.course.organization.id,
            quiz_id=quiz.id,
        )
