import logging

from django.core.management.base import BaseCommand, CommandParser

from django_email_learning.jobs.send_enrollment_reminders_job import (
    SendEnrollmentRemindersJob,
)


class Command(BaseCommand):
    help = "Remind learners whose enrollment is still unverified a while after enrolling, once per enrollment"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging output",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=None,
            help="Hours after enrolling before a reminder is due (default: ENROLLMENT_REMINDERS.AFTER_HOURS, or 24)",
        )
        parser.add_argument(
            "--max-age-days",
            type=int,
            default=None,
            help="Skip enrollments older than this many days (default: ENROLLMENT_REMINDERS.MAX_AGE_DAYS, or 7)",
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
            self.stdout.write("Starting send enrollment reminders job...")
            logger.info("Starting SendEnrollmentRemindersJob")

            job = SendEnrollmentRemindersJob(after_hours=options["hours"], max_age_days=options["max_age_days"])
            job.run()

            self.stdout.write(self.style.SUCCESS("Send enrollment reminders job completed successfully"))
            logger.info("SendEnrollmentRemindersJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Send enrollment reminders job interrupted by user"))
            logger.warning("SendEnrollmentRemindersJob interrupted by user")

        except Exception as e:
            # track_job_execution already records the job_execution_failed
            # metric from inside _run_job; don't double-count it here.
            self.stdout.write(self.style.ERROR(f"Send enrollment reminders job failed: {str(e)}"))
            logger.error(f"SendEnrollmentRemindersJob failed: {str(e)}", exc_info=True)
            raise
