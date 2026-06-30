from unittest.mock import Mock, patch

import pytest

from django_email_learning.services.defaults.email_sender import DjangoEmailSender
from django_email_learning.services.email_sender_service import EmailSenderService


class ConfiguredEmailSender:
    def send_email(self, email) -> None:
        pass


def test_email_sender_service_instantiates_configured_sender_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "EMAIL_SENDER": "tests.services.test_email_sender_service.ConfiguredEmailSender",
        "FROM_EMAIL": "noreply@example.com",
    }

    service = EmailSenderService()

    assert isinstance(service.email_sender, ConfiguredEmailSender)


def test_email_sender_service_uses_prebuilt_configured_sender_object(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "EMAIL_SENDER": "tests.services.test_email_sender_service.ConfiguredEmailSender",
        "FROM_EMAIL": "noreply@example.com",
    }
    prebuilt_sender = Mock()

    with patch(
        "django_email_learning.services.email_sender_service.import_string",
        return_value=prebuilt_sender,
    ):
        service = EmailSenderService()

    assert service.email_sender is prebuilt_sender


def test_email_sender_service_uses_default_sender_when_setting_missing(settings):
    settings.DJANGO_EMAIL_LEARNING = {"FROM_EMAIL": "noreply@example.com"}

    service = EmailSenderService()

    assert isinstance(service.email_sender, DjangoEmailSender)


def test_email_sender_service_uses_default_from_email_when_missing_from_email(settings):
    settings.DJANGO_EMAIL_LEARNING = {"EMAIL_SENDER": "tests.services.test_email_sender_service.ConfiguredEmailSender"}
    settings.DEFAULT_FROM_EMAIL = "default@example.com"

    service = EmailSenderService()

    assert service.from_email == "default@example.com"


def test_email_sender_service_raises_when_no_from_email_available(settings):
    settings.DJANGO_EMAIL_LEARNING = {"EMAIL_SENDER": "tests.services.test_email_sender_service.ConfiguredEmailSender"}
    settings.DEFAULT_FROM_EMAIL = ""

    with pytest.raises(ValueError):
        EmailSenderService()


def test_email_sender_service_send_delegates_to_sender(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "EMAIL_SENDER": "tests.services.test_email_sender_service.ConfiguredEmailSender",
        "FROM_EMAIL": "noreply@example.com",
    }
    sender = Mock()
    service = EmailSenderService()
    service.email_sender = sender

    email = Mock()
    service.send(email)

    sender.send_email.assert_called_once_with(email)
