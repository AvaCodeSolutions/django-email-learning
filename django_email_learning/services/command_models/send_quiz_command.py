from typing import Literal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

from django_email_learning.models import CourseContent
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email


class QuizNotFoundError(Exception):
    pass


class SendQuizCommand(AbstractCommand):
    command_name: Literal["send_quiz"] = "send_quiz"
    link: str
    email: str
    content_id: int

    def execute(self) -> None:
        conf = settings.DJANGO_EMAIL_LEARNING
        content = CourseContent.objects.get(id=self.content_id)
        if not content.quiz:
            raise QuizNotFoundError(f"CourseContent with ID {self.content_id} has no associated quiz")
        self.logger.info(f"Sending quiz with ID {content.quiz.id} to email {mask_email(self.email)}")

        token = self.link.split("token=")[-1] if "token=" in self.link else None
        if token:
            token = token.split("&")[0]  # In case there are other query parameters

        decoded_token = jwt_service.decode_jwt(token) if token else {}

        quiz = content.quiz
        subject = quiz.title
        question_ids = decoded_token.get("question_ids", quiz.questions.values_list("id", flat=True))
        delivery = content.contentdelivery_set.filter(enrollment__learner__email=self.email).first()
        track_open_url = (
            f"{conf['SITE_BASE_URL']}"
            f"{reverse('django_email_learning:personalised:track_open', kwargs={'hash_value': delivery.hash_value})}"
            if delivery
            else None
        )

        context = {
            "quiz": quiz,
            "link": self.link,
            "amp_action_url": (
                f"{conf['SITE_BASE_URL']}{reverse('django_email_learning:api_personalised:quiz_amp_submission')}"
            ),
            "question_ids": question_ids,
            "token": token,
            "unsubscribe_link": content.course.generate_unsubscribe_link(self.email),
            "track_open_url": track_open_url,
            **email_sender_service.organization_footer_context(content.course),
        }
        payload = render_to_string("emails/quiz.txt", context)

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_sender_service.from_email_for_course(content.course),
            to=[self.email],
        )
        email_message.attach_alternative(render_to_string("emails/quiz.html", context), "text/html")
        if conf.get("AMP_ENABLED"):
            email_message.attach_alternative(render_to_string("emails/quiz_amp.html", context), "text/x-amp-html")

        email_sender_service.send(email_message)
        metric_service.quiz_sent(
            course_slug=content.course.slug,
            organization_id=content.course.organization.id,
            quiz_id=quiz.id,
        )
