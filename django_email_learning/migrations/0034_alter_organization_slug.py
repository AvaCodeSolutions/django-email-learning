from django.db import migrations, models

import django_email_learning.models.organizations


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0033_populate_organization_slug"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="The organization's public address, /@<slug>/. Leave blank to generate it from the name. "
                "Changing it breaks links already shared to the old address.",
                unique=True,
                validators=[django_email_learning.models.organizations.organization_slug_validator],
            ),
        ),
    ]
