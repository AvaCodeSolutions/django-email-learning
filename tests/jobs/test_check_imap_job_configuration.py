from unittest.mock import Mock, patch

from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from tests.jobs.imap_interface_mock import ImapInterfaceMock


def test_get_imap_interface_instantiates_configured_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {"IMAP_INTERFACE": "tests.jobs.imap_interface_mock.ImapInterfaceMock"}

    job = CheckIMAPJob()

    assert isinstance(job.imap_interface, ImapInterfaceMock)


def test_get_imap_interface_uses_prebuilt_configured_object(settings):
    settings.DJANGO_EMAIL_LEARNING = {"IMAP_INTERFACE": "tests.jobs.imap_interface_mock.ImapInterfaceMock"}
    prebuilt_interface = Mock()

    with patch(
        "django_email_learning.jobs.check_imap_job.import_string",
        return_value=prebuilt_interface,
    ):
        job = CheckIMAPJob()

    assert job.imap_interface is prebuilt_interface
