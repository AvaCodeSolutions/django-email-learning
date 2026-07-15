import logging

from django.core.management.base import BaseCommand, CommandParser

from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob


class Command(BaseCommand):
    help = "Run the send newsletters job to process due scheduled sendouts"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging output",
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        if options["verbose"]:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
        else:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        logger = logging.getLogger(__name__)

        try:
            self.stdout.write("Starting send newsletters job...")
            logger.info("Starting SendNewslettersJob")

            job = SendNewslettersJob()
            job.run()

            self.stdout.write(self.style.SUCCESS("Send newsletters job completed successfully"))
            logger.info("SendNewslettersJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Send newsletters job interrupted by user"))
            logger.warning("SendNewslettersJob interrupted by user")

        except Exception as e:
            # track_job_execution already records the job_execution_failed
            # metric from inside _run_job; don't double-count it here.
            self.stdout.write(self.style.ERROR(f"Send newsletters job failed: {str(e)}"))
            logger.error(f"SendNewslettersJob failed: {str(e)}", exc_info=True)
            raise
