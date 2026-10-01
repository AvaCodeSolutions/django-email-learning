from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q

from django_email_learning.models import Organization


class Command(BaseCommand):
    help = (
        "Render the favicon PNG of every organization that has a logo but no favicon yet - "
        "organizations whose logo was uploaded before favicons were rendered. Until then their "
        "public pages use the full-size logo as the favicon. --all re-renders every organization."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--all", action="store_true", help="Re-render organizations that already have one")

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        organizations = Organization.objects.exclude(logo="").exclude(logo__isnull=True)
        if not options["all"]:
            organizations = organizations.filter(Q(favicon__isnull=True) | Q(favicon=""))

        rendered = 0
        for organization in organizations:
            organization.refresh_favicon()
            if organization.favicon:
                rendered += 1
            else:
                self.stdout.write(f"No favicon for organization {organization.id}: vector or unreadable logo.")

        self.stdout.write(self.style.SUCCESS(f"Rendered {rendered} favicon(s)."))
