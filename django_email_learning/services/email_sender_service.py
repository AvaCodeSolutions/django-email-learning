from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string


class EmailSenderService:
    def __init__(self) -> None:
        try:
            self.email_sender = import_string(
                settings.DJANGO_EMAIL_LEARNING["EMAIL_SENDER"]
            )
        except (AttributeError, KeyError):
            from django_email_learning.services.defaults.email_sender import (
                DjangoEmailSender,
            )

            self.email_sender = DjangoEmailSender()

        try:
            self.from_email = settings.DJANGO_EMAIL_LEARNING["FROM_EMAIL"]
        except (AttributeError, KeyError):
            try:
                self.from_email = settings.DEFAULT_FROM_EMAIL
            except AttributeError:
                self.from_email = ""
        if not self.from_email:
            raise ValueError(
                "Either set DJANGO_EMAIL_LEARNING['FROM_EMAIL'] or DEFAULT_FROM_EMAIL."
            )

    def send(self, email: EmailMultiAlternatives) -> None:
        self.email_sender.send_email(email)
