from django_email_learning.models import (
    ImapConnection,
    JobExecution,
    JobName,
    JobStatus,
)
from django_email_learning.services.metrics_service import MetricsService
from django_email_learning.ports.imap_interface_protocol import ImapInterfaceProtocol
from django.utils.module_loading import import_string
from django.conf import settings
from django.utils import timezone
import imaplib
import email
from email.policy import default
import logging

logger = logging.getLogger(__name__)
metricc_service = MetricsService()


class CheckIMAPJob:
    def __init__(self) -> None:
        self.imap_interface = self._get_imap_interface()

    def _get_imap_interface(self) -> ImapInterfaceProtocol:
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(
            settings, "DJANGO_EMAIL_LEARNING", {}
        )
        try:
            imap_interface = import_string(
                DJANGO_EMAIL_LEARNING_SETTINGS["IMAP_INTERFACE"]
            )
            return (
                imap_interface() if isinstance(imap_interface, type) else imap_interface
            )
        except KeyError:
            from django_email_learning.services.defaults.imap_interface import (
                ImapInterface,
            )

            return ImapInterface()

    def run(self) -> None:
        if JobExecution.objects.filter(
            job_name=JobName.CHECK_IMAP.value,
            status=JobStatus.RUNNING.value,
        ).exists():
            logger.warning(
                "Another instance of CheckIMAPJob is already running. Exiting this run."
            )
            return
        job_execution = JobExecution.objects.create(
            job_name=JobName.CHECK_IMAP.value,
            status=JobStatus.RUNNING.value,
            started_at=timezone.now(),
        )
        imap_connections = ImapConnection.objects.filter(course__enabled=True)

        for imap_connection in imap_connections:
            account = self._connect_account(imap_connection)
            print(
                f"Checking account {account} for IMAP connection {imap_connection.id}"
            )
            if not account:
                continue

            try:
                folders = list(
                    imap_connection.folders.all().values_list("folder_name", flat=True)
                )
                if "inbox" not in folders:
                    folders.append("inbox")
                for folder in folders:
                    self._process_folder(account, folder, imap_connection)
            finally:
                job_execution.status = JobStatus.COMPLETED.value
                job_execution.finished_at = timezone.now()
                job_execution.save()
                self._logout_account(account, imap_connection)

    def _connect_account(
        self, imap_connection: ImapConnection
    ) -> imaplib.IMAP4_SSL | None:
        try:
            account = imaplib.IMAP4_SSL(imap_connection.server, imap_connection.port)
            account.login(
                imap_connection.email,
                imap_connection.decrypt_password(imap_connection.password),
            )
            return account
        except imaplib.IMAP4.error as e:
            logger.error(
                f"Failed to connect/login to IMAP server for connection {imap_connection.id}: {str(e)}"
            )
            return None

    def _process_folder(
        self, account: imaplib.IMAP4_SSL, folder: str, imap_connection: ImapConnection
    ) -> None:
        try:
            account.select(folder)
            result, data = account.search(None, "UNSEEN")
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP error for connection {imap_connection.id}: {str(e)}")
            return

        if result != "OK":
            logger.warning(
                f"Failed to search unseen emails in folder {folder} for connection {imap_connection.id}"
            )
            return

        mail_ids = data[0].split()
        if not mail_ids:
            logger.info(
                f"No new emails in folder {folder} for connection {imap_connection.id}."
            )
            return

        logger.info(
            f"Found {len(mail_ids)} new emails in folder {folder} for connection {imap_connection.id}."
        )
        for email_id in mail_ids:
            self._process_email(account, email_id, imap_connection)

    def _process_email(
        self,
        account: imaplib.IMAP4_SSL,
        email_id: str,
        imap_connection: ImapConnection,
    ) -> None:
        result, msg_data = account.fetch(email_id, "RFC822")
        if result != "OK":
            logger.warning(
                f"Failed to fetch email with ID {email_id} for connection {imap_connection.id}"
            )
            return

        email_message = email.message_from_bytes(msg_data[0][1], policy=default)  # type: ignore[index, arg-type]
        try:
            self.imap_interface.handle_email_message(email_message, imap_connection)
            account.store(email_id, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error(
                f"Error processing email with ID {email_id} for connection {imap_connection.id}: {str(e)}",
                exc_info=True,
            )
            metricc_service.imap_command_handling_failed(
                imap_connection_id=imap_connection.id,
                organization_id=imap_connection.organization.id,
            )

    def _logout_account(
        self, account: imaplib.IMAP4_SSL, imap_connection: ImapConnection
    ) -> None:
        try:
            account.logout()
        except Exception as e:
            logger.warning(
                f"Failed to logout from IMAP server for connection {imap_connection.id}: {str(e)}"
            )
