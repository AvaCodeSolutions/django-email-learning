import logging
from email.message import EmailMessage

from django_email_learning.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    ImapConnection,
)
from django_email_learning.ports.imap_interface_protocol import ImapInterfaceProtocol
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)

logger = logging.getLogger(__name__)


class ImapInterface(ImapInterfaceProtocol):
    _ACCEPTED_COMMANDS = {"enroll", "drop", "verify"}
    _FUNCTION_MAP = {
        "enroll": "_enroll",
        "drop": "_drop",
        "verify": "_verify",
    }

    def _enroll(self, email: str, argument: str, imap_connection: ImapConnection) -> None:
        logger.info(f"Enrolling {email} with argument '{argument}'")

        try:
            Course.objects.get(
                slug__iexact=argument,
                organization_id=imap_connection.organization.id,
                imap_connection=imap_connection,
            )
        except Course.DoesNotExist:
            logger.warning(
                f"Course with enabled imap connection and slug '{argument}' does not exist"
                f" for organization {imap_connection.organization.id}"
            )
            return

        command = EnrollCommand(
            email=email,
            course_slug=argument,
            organization_id=imap_connection.organization.id,
            case_insensitive_course_slug=True,
        )
        try:
            command.execute()
        except InvalidCourseSlugError as e:
            logger.warning(f"Invalid course slug for email {email}: {str(e)}")
        except EnrollmentAlreadyExistsError as e:
            logger.warning(f"Enrollment already exists for email {email}: {str(e)}")
        except BlockedEmailError as e:
            logger.info(f"Blocked email {email}: {str(e)}")

    def _verify(self, email: str, argument: str, imap_connection: ImapConnection) -> None:
        logger.info(f"Received verify command for {email} with argument '{argument}'")

        try:
            enrollment = Enrollment.objects.get(
                learner__email=email,
                course__organization_id=imap_connection.organization.id,
                course__enabled=True,
                activation_code=argument,
                status=EnrollmentStatus.UNVERIFIED,
            )
        except Enrollment.DoesNotExist:
            logger.warning(
                f"No unverified enrollment found for email {email} in organization {imap_connection.organization.id}"
            )
            return
        command = VerifyEnrollmentCommand(
            enrollment_id=enrollment.id,
            verification_code=argument,
        )

        command.execute()

    def _drop(self, email: str, argument: str, imap_connection: ImapConnection) -> None:
        logger.info(f"Received drop command for {email} with argument '{argument}'")

        command = UnsubscribeCommand(
            email=email,
            course_slug=argument,
            organization_id=imap_connection.organization.id,
            case_insensitive_course_slug=True,
        )

        command.execute()

    def handle_email_message(self, email_message: EmailMessage, imap_connection: ImapConnection) -> None:
        # Implement your email handling logic here

        logger.info(
            f"Handling email from {email_message['From']} with subject {email_message['Subject']}"
            f" for connection {imap_connection.email}"
        )
        subject = email_message["Subject"]
        subject_parts = subject.split()
        if len(subject_parts) < 2:
            logger.warning(f"Invalid email subject format: '{subject}'. Expected format: 'command argument'")
            return

        if subject_parts[0].lower() not in self._ACCEPTED_COMMANDS:
            logger.warning(
                f"Invalid command in email subject: '{subject_parts[0]}'."
                f" Expected one of: {', '.join(self._ACCEPTED_COMMANDS)}"
            )
            return

        command = subject_parts[0].lower()
        argument = subject_parts[1]

        handler_function = self._FUNCTION_MAP.get(command)
        if handler_function:
            email = email_message["From"].addresses[0].addr_spec
            getattr(self, handler_function)(email, argument, imap_connection)
