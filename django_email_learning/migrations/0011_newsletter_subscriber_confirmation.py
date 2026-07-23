# Generated manually - adds NewsletterSubscriber.confirmed_at/confirm_token
# for double opt-in. Existing subscribers (added before this feature existed)
# are grandfathered in as confirmed at their original subscribed_at time,
# since there's no way to retroactively confirm them and revoking their
# subscription unilaterally would be its own breaking change.

import uuid

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def populate_confirm_tokens(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    NewsletterSubscriber = apps.get_model("django_email_learning", "NewsletterSubscriber")
    for subscriber in NewsletterSubscriber.objects.all().only("id"):
        subscriber.confirm_token = uuid.uuid4()
        subscriber.save(update_fields=["confirm_token"])


def backfill_confirmed_at(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    NewsletterSubscriber = apps.get_model("django_email_learning", "NewsletterSubscriber")
    NewsletterSubscriber.objects.update(confirmed_at=models.F("subscribed_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0010_organization_embed_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="newslettersubscriber",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="newslettersubscriber",
            name="confirm_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_confirm_tokens, migrations.RunPython.noop),
        migrations.RunPython(backfill_confirmed_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="newslettersubscriber",
            name="confirm_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
