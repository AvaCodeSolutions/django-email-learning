import pytest

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob


@pytest.fixture
def test_delivery_queue():
    return DeliverContentsJob()
