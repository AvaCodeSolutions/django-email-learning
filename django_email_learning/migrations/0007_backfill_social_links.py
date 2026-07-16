from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

FIELD_TO_PLATFORM = {
    "website": "website",
    "youtube_channel": "youtube",
    "linkedin_page": "linkedin",
}


def backfill_social_links(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Organization = apps.get_model("django_email_learning", "Organization")
    SocialLink = apps.get_model("django_email_learning", "SocialLink")

    social_links = []
    for organization in Organization.objects.all():
        for field_name, platform in FIELD_TO_PLATFORM.items():
            url = getattr(organization, field_name)
            if url:
                social_links.append(SocialLink(organization=organization, platform=platform, url=url))
    SocialLink.objects.bulk_create(social_links)


def restore_legacy_fields(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Organization = apps.get_model("django_email_learning", "Organization")
    SocialLink = apps.get_model("django_email_learning", "SocialLink")

    for organization in Organization.objects.all():
        update_fields = []
        for field_name, platform in FIELD_TO_PLATFORM.items():
            social_link = SocialLink.objects.filter(organization=organization, platform=platform).first()
            if social_link:
                setattr(organization, field_name, social_link.url)
                update_fields.append(field_name)
        if update_fields:
            organization.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0006_sociallink"),
    ]

    operations = [
        migrations.RunPython(backfill_social_links, restore_legacy_fields),
    ]
