from typing import Protocol
from django.core.mail import EmailMultiAlternatives


class EmailSenderProtocol(Protocol):
    def send_email(self, email: EmailMultiAlternatives) -> None:
        ...
