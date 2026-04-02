from django.core.management.base import BaseCommand
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django.core.management.base import CommandParser
import logging


class Command(BaseCommand):
    help = "Check the IMAP connection for all courses and execute valid email commands"

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
            self.stdout.write("Starting check IMAP job...")
            logger.info("Starting Check IMAP job")

            job = CheckIMAPJob()
            job.run()

            self.stdout.write(
                self.style.SUCCESS("Check IMAP job completed successfully")
            )
            logger.info("Check IMAP job completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Check IMAP job interrupted by user"))
            logger.warning("Check IMAP job interrupted by user")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Check IMAP job failed: {str(e)}"))
            logger.error(f"Check IMAP job failed: {str(e)}", exc_info=True)
            raise
