from datetime import timedelta

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from django_email_learning.models import JobExecution, JobStatus


class Command(BaseCommand):
    help = "Delete old completed JobExecution rows to limit table growth"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=2,
            help="Delete completed job executions finished more than this many days ago",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many rows would be deleted without deleting them",
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        days = options["days"]
        dry_run = options["dry_run"]

        if days <= 0:
            self.stdout.write(self.style.ERROR("--days must be a positive integer"))
            return

        cutoff = timezone.now() - timedelta(days=days)
        queryset = JobExecution.objects.filter(
            status__in=[JobStatus.COMPLETED.value, JobStatus.STALE.value],
            finished_at__isnull=False,
            finished_at__lt=cutoff,
        )

        candidate_count = queryset.count()

        if dry_run:
            self.stdout.write(
                f"Dry run: {candidate_count} completed/staled job executions older than {days} days would be deleted."
            )
            return

        deleted_count, _ = queryset.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} completed/staled job executions older than {days} days."
            )
        )
