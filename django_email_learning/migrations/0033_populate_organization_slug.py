from django.conf import settings
from django.db import migrations
from django.db.models import Q
from django.utils.text import slugify

# Frozen copies of the generator's rules as they stood when this migration was
# written, so later changes to the model code cannot change what it does.
SLUG_MAX_LENGTH = 50
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


def plan_slugs(organizations, taken, reserved):  # type: ignore[no-untyped-def]
    """Maps each (id, name) in ``organizations`` to its slug, in the order given,
    avoiding ``taken``, ``reserved`` and the slugs handed out before it.
    """
    taken = set(taken)
    plan = {}
    for organization_id, name in organizations:
        base = slugify(name) or "organization"
        candidate = base[:SLUG_MAX_LENGTH].strip("-")
        counter = 1
        while candidate in reserved or candidate in taken:
            counter += 1
            suffix = f"-{counter}"
            candidate = f"{base[: SLUG_MAX_LENGTH - len(suffix)].strip('-')}{suffix}"
        taken.add(candidate)
        plan[organization_id] = candidate
    return plan


def populate_slugs(apps, schema_editor):  # type: ignore[no-untyped-def]
    """Gives every organization a slug from its name, oldest first, so when two
    names slugify alike the older organization keeps the plain slug and the
    newer one gets ``-2``.
    """
    Organization = apps.get_model("django_email_learning", "Organization")
    conf = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    reserved = frozenset(conf.get("RESERVED_ORGANIZATION_SLUGS", DEFAULT_RESERVED_SLUGS))
    missing = Q(slug__isnull=True) | Q(slug="")
    plan = plan_slugs(
        Organization.objects.filter(missing).order_by("id").values_list("id", "name"),
        taken=Organization.objects.exclude(missing).values_list("slug", flat=True),
        reserved=reserved,
    )
    for organization_id, slug in plan.items():
        Organization.objects.filter(pk=organization_id).update(slug=slug)


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0032_organization_slug"),
    ]

    operations = [
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
    ]
