from django.db import migrations, models


class Migration(migrations.Migration):
    """Tightens the backfilled columns and drops the reversible key storage.

    After this runs the deployment no longer holds anything that can be turned
    back into a usable credential.
    """

    dependencies = [
        ("django_email_learning", "0018_backfill_api_key_hashes"),
    ]

    operations = [
        migrations.RemoveField(model_name="apikey", name="key"),
        migrations.RemoveField(model_name="apikey", name="salt"),
        migrations.AlterField(
            model_name="apikey",
            name="key_type",
            field=models.CharField(
                choices=[("platform", "Platform"), ("organization", "Organization")],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="key_id",
            field=models.CharField(editable=False, max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="secret_hash",
            field=models.CharField(editable=False, max_length=64, unique=True),
        ),
        migrations.AlterModelOptions(
            name="apikey",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="apikey",
            constraint=models.CheckConstraint(
                condition=models.Q(("key_type", "platform"), ("organization__isnull", True))
                | models.Q(("key_type", "organization"), ("organization__isnull", False)),
                name="api_key_organization_matches_key_type",
            ),
        ),
    ]
