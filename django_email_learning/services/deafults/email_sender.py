import logging
from django_email_learning.ports.email_sender_protocol import EmailSenderProtocol
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


class DjangoEmailSender(EmailSenderProtocol):
    def _mask_email(self, email_address: str) -> str:
        """Mask email address for logging privacy."""
        try:
            username, domain = email_address.split("@")
            masked_username = username[0] + "***"
            return f"{masked_username}@{domain}"
        except ValueError:
            return "***@***"

    def _mask_recipients(self, recipients: list[str]) -> str:
        """Mask all recipient email addresses for logging."""
        if not recipients:
            return "no recipients"
        masked = [self._mask_email(recipient) for recipient in recipients]
        return ", ".join(masked)

    def send_email(self, email: EmailMultiAlternatives) -> None:
        masked_recipients = self._mask_recipients(email.to)
        try:
            logger.info(f"Sending email to {masked_recipients}")
            email.send()
            logger.info(f"Email sent successfully to {masked_recipients}")
        except Exception as e:
            logger.error(f"Failed to send email to {masked_recipients}: {str(e)}")
            raise
