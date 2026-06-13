from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0033_alter_jobexecution_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentdelivery",
            name="opened_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
