from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string


class EmailSenderService:
    def __init__(self) -> None:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            configured_email_sender = import_string(
                DJANGO_EMAIL_LEARNING_SETTINGS["EMAIL_SENDER"]
            )
            self.email_sender = (
                configured_email_sender()
                if isinstance(configured_email_sender, type)
                else configured_email_sender
            )
        except KeyError:
            from django_email_learning.services.defaults.email_sender import (
                DjangoEmailSender,
            )

            self.email_sender = DjangoEmailSender()

        try:
            self.from_email = DJANGO_EMAIL_LEARNING_SETTINGS["FROM_EMAIL"]
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
