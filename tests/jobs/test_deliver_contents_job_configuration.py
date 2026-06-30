from unittest.mock import Mock, patch

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from tests.jobs.delivery_queue_mock import DeliveryQueueMock


def test_get_delivery_queue_instantiates_configured_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {"DELIVERY_QUEUE": "tests.jobs.delivery_queue_mock.DeliveryQueueMock"}

    job = DeliverContentsJob()

    assert isinstance(job.delivery_queue, DeliveryQueueMock)


def test_get_delivery_queue_uses_prebuilt_configured_object(settings):
    settings.DJANGO_EMAIL_LEARNING = {"DELIVERY_QUEUE": "tests.jobs.delivery_queue_mock.DeliveryQueueMock"}
    prebuilt_queue = Mock()

    with patch(
        "django_email_learning.jobs.queue_utils.import_string",
        return_value=prebuilt_queue,
    ):
        job = DeliverContentsJob()

    assert job.delivery_queue is prebuilt_queue
