import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Adds the new ApiKey columns as nullable so 0018 can backfill them.

    Split across three migrations because the backfill in 0018 has to read the
    old encrypted `key` column, which 0019 then drops.
    """

    dependencies = [
        ("django_email_learning", "0016_alter_organization_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="apikey",
            name="key_type",
            field=models.CharField(
                choices=[("platform", "Platform"), ("organization", "Organization")],
                db_index=True,
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_keys",
                to="django_email_learning.organization",
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="name",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="key_id",
            field=models.CharField(editable=False, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="secret_hash",
            field=models.CharField(editable=False, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="scopes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="apikey",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="last_used_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
