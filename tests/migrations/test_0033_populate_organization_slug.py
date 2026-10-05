import importlib

from django.apps import apps

from django_email_learning.models import Organization

migration = importlib.import_module("django_email_learning.migrations.0033_populate_organization_slug")


def test_plan_slugifies_each_name():
    plan = migration.plan_slugs([(1, "My Organization"), (2, "Acme Academy")], taken=[], reserved=())
    assert plan == {1: "my-organization", 2: "acme-academy"}


def test_plan_gives_the_first_organization_the_plain_slug():
    assert migration.plan_slugs([(1, "Acme"), (2, "ACME")], taken=[], reserved=()) == {1: "acme", 2: "acme-2"}


def test_plan_avoids_taken_and_reserved_slugs():
    plan = migration.plan_slugs([(1, "Acme"), (2, "Support")], taken=["acme"], reserved={"support"})
    assert plan == {1: "acme-2", 2: "support-2"}


def test_plan_falls_back_for_a_name_with_nothing_to_slugify():
    assert migration.plan_slugs([(1, "آکادمی")], taken=[], reserved=()) == {1: "organization"}


def test_plan_keeps_the_suffix_within_the_max_length():
    plan = migration.plan_slugs([(1, "a" * 80)], taken=["a" * 50], reserved=())
    assert plan == {1: f"{'a' * 48}-2"}


def test_populate_fills_a_missing_slug_and_leaves_the_others(db):
    acme = Organization.objects.create(name="Acme")
    Organization.objects.filter(pk=acme.pk).update(slug="")

    migration.populate_slugs(apps, None)

    acme.refresh_from_db()
    assert acme.slug == "acme"
    assert Organization.objects.get(id=1).slug == "my-organization"


def test_populate_avoids_existing_slugs_and_reads_the_reserved_setting(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "RESERVED_ORGANIZATION_SLUGS": ["support"],
    }
    Organization.objects.create(name="Something", slug="support-2")
    support = Organization.objects.create(name="Support", slug="placeholder")
    Organization.objects.filter(pk=support.pk).update(slug="")

    migration.populate_slugs(apps, None)

    support.refresh_from_db()
    assert support.slug == "support-3"
