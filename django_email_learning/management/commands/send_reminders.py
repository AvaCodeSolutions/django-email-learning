from django.core.management.base import BaseCommand
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django.core.management.base import CommandParser
import logging

from django_email_learning.models import JobName
from django_email_learning.services.metrics_service import metric_service


class Command(BaseCommand):
    help = "Run the send reminders job to process scheduled reminders"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging output",
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        # Configure logging based on verbosity
        if options["verbose"]:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        else:
            logging.basicConfig(
                level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
            )

        logger = logging.getLogger(__name__)

        try:
            self.stdout.write("Starting send reminders job...")
            logger.info("Starting SendRemindersJob")

            job = SendRemindersJob()
            job.run()

            self.stdout.write(
                self.style.SUCCESS("Send reminders job completed successfully")
            )
            logger.info("SendRemindersJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("Send reminders job interrupted by user")
            )
            logger.warning("SendRemindersJob interrupted by user")

        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.SEND_REMINDERS.value)
            self.stdout.write(self.style.ERROR(f"Send reminders job failed: {str(e)}"))
            logger.error(f"SendRemindersJob failed: {str(e)}", exc_info=True)
            raise
