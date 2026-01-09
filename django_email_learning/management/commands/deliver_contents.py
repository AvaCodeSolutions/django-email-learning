from django.core.management.base import BaseCommand
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django.core.management.base import CommandParser
import logging


class Command(BaseCommand):
    help = "Run the content delivery job to process scheduled content deliveries"

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
            self.stdout.write("Starting content delivery job...")
            logger.info("Starting DeliverContentsJob")

            job = DeliverContentsJob()
            job.run()

            self.stdout.write(
                self.style.SUCCESS("Content delivery job completed successfully")
            )
            logger.info("DeliverContentsJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("Content delivery job interrupted by user")
            )
            logger.warning("DeliverContentsJob interrupted by user")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Content delivery job failed: {str(e)}")
            )
            logger.error(f"DeliverContentsJob failed: {str(e)}", exc_info=True)
            raise
