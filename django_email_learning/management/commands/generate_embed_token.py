from django.core.management.base import BaseCommand, CommandParser

from django_email_learning.models import Organization


class Command(BaseCommand):
    help = (
        "Generate (or rotate) the embed_token for an organization, used to authorize the "
        "cross-origin embeddable enroll/newsletter-subscribe API. Rotating overwrites the "
        "existing token, immediately invalidating it for anyone still using the old value."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("organization_id", type=int, help="ID of the organization to generate a token for")

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        organization_id = options["organization_id"]
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Organization {organization_id} does not exist."))
            return

        organization.embed_token = Organization.generate_embed_token()
        organization.save(update_fields=["embed_token"])

        self.stdout.write(self.style.SUCCESS(f"Embed token for organization {organization_id} ({organization.name}):"))
        self.stdout.write(organization.embed_token)
