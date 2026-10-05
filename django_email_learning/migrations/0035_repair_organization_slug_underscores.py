import re

from django.conf import settings
from django.db import migrations

# Frozen copies of the generator's rules as they stood when this migration was
# written, so later changes to the model code cannot change what it does.
SLUG_MAX_LENGTH = 50
VALID_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_RESERVED_SLUGS = (
    "admin",
    "administrator",
    "api",
    "help",
    "official",
    "platform",
    "public",
    "staff",
    "support",
    "system",
)


def plan_repairs(organizations, taken, reserved):  # type: ignore[no-untyped-def]
    """Maps each (id, slug) in ``organizations`` whose slug the validator rejects
    to a valid one, in the order given: runs of underscores and hyphens become a
    single hyphen, avoiding ``taken``, ``reserved`` and the slugs handed out
    before it. Valid slugs are left out of the plan.
    """
    taken = set(taken)
    plan = {}
    for organization_id, slug in organizations:
        if VALID_SLUG.match(slug):
            continue
        base = re.sub(r"[-_]+", "-", slug.lower()).strip("-") or "organization"
        candidate = base[:SLUG_MAX_LENGTH].strip("-")
        counter = 1
        while candidate in reserved or candidate in taken:
            counter += 1
            suffix = f"-{counter}"
            candidate = f"{base[: SLUG_MAX_LENGTH - len(suffix)].strip('-')}{suffix}"
        taken.add(candidate)
        plan[organization_id] = candidate
    return plan


def repair_slugs(apps, schema_editor):  # type: ignore[no-untyped-def]
    """0033 and the model's generator kept the underscores slugify leaves in a
    name, giving slugs such as ``acme_academy`` that the slug validator rejects,
    so the organization could not be saved through a form. Rewrites them as
    ``acme-academy``, oldest organization first.
    """
    Organization = apps.get_model("django_email_learning", "Organization")
    conf = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    reserved = frozenset(conf.get("RESERVED_ORGANIZATION_SLUGS", DEFAULT_RESERVED_SLUGS))
    organizations = list(Organization.objects.order_by("id").values_list("id", "slug"))
    plan = plan_repairs(
        organizations,
        taken=[slug for _, slug in organizations if VALID_SLUG.match(slug)],
        reserved=reserved,
    )
    for organization_id, slug in plan.items():
        Organization.objects.filter(pk=organization_id).update(slug=slug)


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0034_alter_organization_slug"),
    ]

    operations = [
        migrations.RunPython(repair_slugs, migrations.RunPython.noop),
    ]
