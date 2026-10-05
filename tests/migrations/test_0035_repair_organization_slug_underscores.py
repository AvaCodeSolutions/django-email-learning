import importlib

from django.apps import apps

from django_email_learning.models import Organization

migration = importlib.import_module("django_email_learning.migrations.0035_repair_organization_slug_underscores")


def test_plan_turns_underscores_into_single_hyphens_and_skips_valid_slugs():
    plan = migration.plan_repairs(
        [(1, "my-organization"), (2, "acme_academy"), (3, "_a__-_b_"), (4, "___")], taken=[], reserved=()
    )
    assert plan == {2: "acme-academy", 3: "a-b", 4: "organization"}


def test_plan_avoids_taken_reserved_and_earlier_repaired_slugs():
    plan = migration.plan_repairs(
        [(1, "acme_academy"), (2, "acme__academy"), (3, "_support")], taken=["acme-academy"], reserved={"support"}
    )
    assert plan == {1: "acme-academy-2", 2: "acme-academy-3", 3: "support-2"}


def test_plan_keeps_the_suffix_within_the_max_length():
    plan = migration.plan_repairs([(1, f"{'a' * 49}_")], taken=["a" * 49], reserved=())
    assert plan == {1: f"{'a' * 48}-2"}


def test_repair_rewrites_only_invalid_slugs(db):
    acme = Organization.objects.create(name="Acme Academy")
    Organization.objects.filter(pk=acme.pk).update(slug="acme_academy")
    other = Organization.objects.create(name="Acme-Academy", slug="acme-academy-x")

    migration.repair_slugs(apps, None)

    acme.refresh_from_db()
    other.refresh_from_db()
    assert acme.slug == "acme-academy"
    assert other.slug == "acme-academy-x"
    assert Organization.objects.get(id=1).slug == "my-organization"
    acme.full_clean()
