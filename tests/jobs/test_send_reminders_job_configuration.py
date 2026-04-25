from unittest.mock import Mock, patch

from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from tests.jobs.delivery_queue_mock import DeliveryQueueMock


def test_get_reminder_queue_instantiates_configured_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "REMINDER_QUEUE": "tests.jobs.delivery_queue_mock.DeliveryQueueMock"
    }

    job = SendRemindersJob()

    assert isinstance(job.reminder_queue, DeliveryQueueMock)


def test_get_reminder_queue_uses_prebuilt_configured_object(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "REMINDER_QUEUE": "tests.jobs.delivery_queue_mock.DeliveryQueueMock"
    }
    prebuilt_queue = Mock()

    with patch(
        "django_email_learning.jobs.send_reminders_job.import_string",
        return_value=prebuilt_queue,
    ):
        job = SendRemindersJob()

    assert job.reminder_queue is prebuilt_queue
