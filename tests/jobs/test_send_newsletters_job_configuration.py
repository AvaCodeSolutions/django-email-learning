from unittest.mock import Mock, patch

from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob


class _FakeSendoutQueue:
    def next_task(self):
        return None


def test_get_sendout_queue_instantiates_configured_class(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "SENDOUT_QUEUE": "tests.jobs.test_send_newsletters_job_configuration._FakeSendoutQueue"
    }

    job = SendNewslettersJob()

    assert isinstance(job.sendout_queue, _FakeSendoutQueue)


def test_get_sendout_queue_uses_prebuilt_configured_object(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        "SENDOUT_QUEUE": "tests.jobs.test_send_newsletters_job_configuration._FakeSendoutQueue"
    }
    prebuilt_queue = Mock()

    with patch(
        "django_email_learning.jobs.queue_utils.import_string",
        return_value=prebuilt_queue,
    ):
        job = SendNewslettersJob()

    assert job.sendout_queue is prebuilt_queue
