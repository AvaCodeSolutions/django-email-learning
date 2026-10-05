from django.db import migrations, models

import django_email_learning.models.organizations


class Migration(migrations.Migration):
    """Adds Organization.slug, nullable for now: 0033 fills it for the existing
    organizations and 0034 makes it required.
    """

    dependencies = [
        ("django_email_learning", "0031_organization_favicon"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="The organization's public address, /@<slug>/. Leave blank to generate it from the name. "
                "Changing it breaks links already shared to the old address.",
                null=True,
                unique=True,
                validators=[django_email_learning.models.organizations.organization_slug_validator],
            ),
        ),
    ]
