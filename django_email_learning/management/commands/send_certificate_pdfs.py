import logging

from django.core.management.base import BaseCommand, CommandParser

from django_email_learning.jobs.send_certificate_pdfs_job import SendCertificatePdfsJob
from django_email_learning.models import JobName
from django_email_learning.services.metrics_service import metric_service


class Command(BaseCommand):
    help = "Run the send certificate PDFs job to email pending certificate PDFs"

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
            self.stdout.write("Starting send certificate PDFs job...")
            logger.info("Starting SendCertificatePdfsJob")

            job = SendCertificatePdfsJob()
            job.run()

            self.stdout.write(self.style.SUCCESS("Send certificate PDFs job completed successfully"))
            logger.info("SendCertificatePdfsJob completed successfully")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Send certificate PDFs job interrupted by user"))
            logger.warning("SendCertificatePdfsJob interrupted by user")

        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.SEND_CERTIFICATE_PDFS.value)
            self.stdout.write(self.style.ERROR(f"Send certificate PDFs job failed: {str(e)}"))
            logger.error(f"SendCertificatePdfsJob failed: {str(e)}", exc_info=True)
            raise
