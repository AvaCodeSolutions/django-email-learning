import logging

from django.core.management.base import BaseCommand, CommandParser

from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)


class Command(BaseCommand):
    help = "Run the deactivate inactive enrollments job to deactivate enrollments that have missed quiz deadlines"

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
            logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        logger = logging.getLogger(__name__)

        try:
            self.stdout.write("Starting deactivate inactive enrollments job...")
            logger.info("Starting DeactivateInactiveEnrollmentsJob")

            job = DeactivateInactiveEnrollmentsJob()
            job.run()

            self.stdout.write(self.style.SUCCESS("Deactivate inactive enrollments job completed successfully"))
            logger.info("DeactivateInactiveEnrollmentsJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Deactivate inactive enrollments job interrupted by user"))
            logger.warning("DeactivateInactiveEnrollmentsJob interrupted by user")

        except Exception as e:
            # track_job_execution already records the job_execution_failed
            # metric from inside _run_job; don't double-count it here.
            self.stdout.write(self.style.ERROR(f"Deactivate inactive enrollments job failed: {str(e)}"))
            logger.error(f"DeactivateInactiveEnrollmentsJob failed: {str(e)}", exc_info=True)
            raise
