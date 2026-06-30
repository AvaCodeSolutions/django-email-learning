from unittest.mock import Mock

import pytest
from django.core.mail import EmailMultiAlternatives

from django_email_learning.services.defaults.email_sender import DjangoEmailSender


@pytest.fixture
def email_sender() -> DjangoEmailSender:
    return DjangoEmailSender()


@pytest.fixture
def email_multi_alternatives() -> EmailMultiAlternatives:
    email = Mock(spec=EmailMultiAlternatives)
    email.to = ["recipient@example.com"]
    return email


def test_email_sender_logs_success_with_masked_recipients(
    email_sender: DjangoEmailSender,
    email_multi_alternatives: EmailMultiAlternatives,
    caplog,
):
    with caplog.at_level("INFO"):
        email_sender.send_email(email_multi_alternatives)
    assert "Sending email to r***@example.com" in caplog.text


def test_email_sender_logs_failure_with_masked_recipients(
    email_sender: DjangoEmailSender,
    email_multi_alternatives: EmailMultiAlternatives,
    caplog,
):
    email_multi_alternatives.send.side_effect = Exception("SMTP error")

    with caplog.at_level("ERROR"):
        with pytest.raises(Exception):
            email_sender.send_email(email_multi_alternatives)

    assert "Failed to send email to r***@example.com" in caplog.text
