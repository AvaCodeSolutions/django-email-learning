from typing import Protocol
from email.message import EmailMessage
from django_email_learning.models import ImapConnection


class ImapInterfaceProtocol(Protocol):
    def handle_email_message(
        self, email_message: EmailMessage, imap_connection: ImapConnection
    ) -> None: ...
