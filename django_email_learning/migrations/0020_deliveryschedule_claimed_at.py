from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0019_apikey_drop_encrypted_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryschedule",
            name="claimed_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text=("When the schedule was moved to PROCESSING. Used to recover claims whose worker died."),
                null=True,
            ),
        ),
    ]
