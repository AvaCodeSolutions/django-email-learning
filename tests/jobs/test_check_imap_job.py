import imaplib
from unittest.mock import MagicMock, call, patch

import django_email_learning.jobs.check_imap_job as check_imap_job_module
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.models import InboxFolder, JobExecution, JobName, JobStatus


def test_check_imap_job_processes_unseen_emails(db, course, imap_connection):
    course.enabled = True
    course.save()

    InboxFolder.objects.create(imap_connection=imap_connection, folder_name="alerts")

    imap_interface_mock = MagicMock()
    account_mock = MagicMock()
    account_mock.search.side_effect = [
        ("OK", [b"1 2"]),
        ("OK", [b""]),
    ]
    raw_email = (
        b"From: sender@example.com\r\n"
        b"To: user@example.com\r\n"
        b"Subject: Test\r\n\r\n"
        b"Hello"
    )
    account_mock.fetch.side_effect = [
        ("OK", [(None, raw_email)]),
        ("OK", [(None, raw_email)]),
    ]

    with (
        patch.object(
            CheckIMAPJob,
            "_get_imap_interface",
            return_value=imap_interface_mock,
        ),
        patch(
            "django_email_learning.jobs.check_imap_job.imaplib.IMAP4_SSL",
            return_value=account_mock,
        ),
    ):
        job = CheckIMAPJob()
        job.run()

    account_mock.login.assert_called_once()
    account_mock.select.assert_has_calls([call("alerts"), call("inbox")])
    assert imap_interface_mock.handle_email_message.call_count == 2
    account_mock.store.assert_has_calls(
        [call(b"1", "+FLAGS", "\\Seen"), call(b"2", "+FLAGS", "\\Seen")]
    )
    account_mock.logout.assert_called_once()


def test_check_imap_job_skips_connection_when_login_fails(db, course, imap_connection):
    course.enabled = True
    course.save()

    imap_interface_mock = MagicMock()

    with (
        patch.object(
            CheckIMAPJob,
            "_get_imap_interface",
            return_value=imap_interface_mock,
        ),
        patch(
            "django_email_learning.jobs.check_imap_job.imaplib.IMAP4_SSL",
            side_effect=imaplib.IMAP4.error("login failed"),
        ),
    ):
        job = CheckIMAPJob()
        job.run()

    imap_interface_mock.handle_email_message.assert_not_called()


def test_check_imap_job_tracks_metric_when_processing_fails(
    db, course, imap_connection
):
    course.enabled = True
    course.save()

    imap_interface_mock = MagicMock()
    imap_interface_mock.handle_email_message.side_effect = Exception(
        "processing failed"
    )

    account_mock = MagicMock()
    account_mock.search.return_value = ("OK", [b"1"])
    raw_email = (
        b"From: sender@example.com\r\n"
        b"To: user@example.com\r\n"
        b"Subject: Test\r\n\r\n"
        b"Hello"
    )
    account_mock.fetch.return_value = ("OK", [(None, raw_email)])

    with (
        patch.object(
            CheckIMAPJob,
            "_get_imap_interface",
            return_value=imap_interface_mock,
        ),
        patch(
            "django_email_learning.jobs.check_imap_job.imaplib.IMAP4_SSL",
            return_value=account_mock,
        ),
        patch.object(
            check_imap_job_module.metric_service,
            "imap_command_handling_failed",
        ) as metric_spy,
    ):
        job = CheckIMAPJob()
        job.run()

    metric_spy.assert_called_once_with(
        imap_connection_id=imap_connection.id,
        organization_id=imap_connection.organization.id,
    )
    account_mock.store.assert_not_called()
    account_mock.logout.assert_called_once()


def test_check_imap_job_triggers_started_metric(db):
    with (
        patch(
            "django_email_learning.jobs.check_imap_job.imaplib.IMAP4_SSL",
            side_effect=Exception("no connection"),
        ),
        patch.object(
            check_imap_job_module.metric_service,
            "job_execution_started",
        ) as metric_started_spy,
    ):
        job = CheckIMAPJob()
        job.run()

    metric_started_spy.assert_called_once_with(job_name="check_imap")


def test_check_imap_job_triggers_finished_metric(db):
    with (
        patch(
            "django_email_learning.jobs.check_imap_job.imaplib.IMAP4_SSL",
            side_effect=Exception("no connection"),
        ),
        patch.object(
            check_imap_job_module.metric_service,
            "job_execution_finished",
        ) as metric_finished_spy,
    ):
        job = CheckIMAPJob()
        job.run()

    metric_finished_spy.assert_called_once()
    call_kwargs = metric_finished_spy.call_args
    assert call_kwargs.kwargs["job_name"] == "check_imap"
    assert isinstance(call_kwargs.kwargs["execution_time"], int)


def test_check_imap_job_does_not_emit_start_or_finish_metrics_when_already_running(db):
    JobExecution.objects.create(
        job_name=JobName.CHECK_IMAP.value,
        status=JobStatus.RUNNING.value,
    )

    with (
        patch.object(
            check_imap_job_module.metric_service,
            "job_execution_started",
        ) as metric_started_spy,
        patch.object(
            check_imap_job_module.metric_service,
            "job_execution_finished",
        ) as metric_finished_spy,
    ):
        CheckIMAPJob().run()

    metric_started_spy.assert_not_called()
    metric_finished_spy.assert_not_called()
