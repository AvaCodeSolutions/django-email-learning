import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django_email_learning.models import Organization
from django_email_learning.models.organizations import (
    DEFAULT_RESERVED_ORGANIZATION_SLUGS,
    generate_organization_slug,
)


def never_taken(slug: str) -> bool:
    return False


def test_generate_slugifies_the_name():
    assert generate_organization_slug("Acme Academy!", never_taken, reserved=()) == "acme-academy"


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Acme_Academy", "acme-academy"),
        ("Acme__ - _Academy", "acme-academy"),
        ("_Acme_", "acme"),
        ("___", "organization"),
    ],
)
def test_generate_turns_underscores_into_single_hyphens(name, slug):
    assert generate_organization_slug(name, never_taken, reserved=()) == slug


def test_create_accepts_a_name_with_underscores(db):
    assert Organization.objects.create(name="Professional/past_due").slug == "professionalpast-due"


def test_generate_appends_a_counter_when_the_slug_is_taken():
    taken = {"acme", "acme-2"}
    assert generate_organization_slug("Acme", taken.__contains__, reserved=()) == "acme-3"


def test_generate_skips_reserved_slugs():
    assert generate_organization_slug("Support", never_taken, reserved=["support"]) == "support-2"


def test_generate_falls_back_when_nothing_slugifies():
    assert generate_organization_slug("آکادمی", never_taken, reserved=()) == "organization"


def test_generate_keeps_the_suffix_within_the_max_length():
    name = "a" * 80
    slug = generate_organization_slug(name, {"a" * 50}.__contains__, reserved=())
    assert slug == f"{'a' * 48}-2"


def test_generate_does_not_end_a_truncated_slug_with_a_hyphen():
    name = f"{'a' * 49} b"
    assert generate_organization_slug(name, never_taken, reserved=()) == "a" * 49


def test_default_organization_has_a_slug(db):
    assert Organization.objects.get(id=1).slug == "my-organization"


def test_create_generates_a_slug_from_the_name(db):
    assert Organization.objects.create(name="Acme Academy").slug == "acme-academy"


def test_create_gives_a_same_named_organization_the_next_slug(db):
    Organization.objects.create(name="Acme")
    assert Organization.objects.create(name="ACME").slug == "acme-2"


def test_create_avoids_the_default_reserved_slugs(db):
    assert "admin" in DEFAULT_RESERVED_ORGANIZATION_SLUGS
    assert Organization.objects.create(name="Admin").slug == "admin-2"


def test_reserved_slugs_setting_replaces_the_defaults(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "RESERVED_ORGANIZATION_SLUGS": ["inbox-academy"],
    }
    assert Organization.objects.create(name="Inbox Academy").slug == "inbox-academy-2"
    assert Organization.objects.create(name="Admin").slug == "admin"


def test_renaming_keeps_the_slug(db):
    organization = Organization.objects.create(name="Acme")
    organization.name = "Globex"
    organization.save()
    organization.refresh_from_db()
    assert organization.slug == "acme"


def test_an_explicit_slug_is_kept(db):
    assert Organization.objects.create(name="Acme", slug="acme-learning").slug == "acme-learning"


def test_an_explicit_duplicate_slug_is_rejected(db):
    Organization.objects.create(name="Acme")
    with pytest.raises(ValidationError):
        Organization.objects.create(name="Other", slug="acme")


@pytest.mark.parametrize("slug", ["Acme", "acme_learning", "-acme", "acme--learning", "acme-"])
def test_a_malformed_slug_is_rejected(db, slug):
    with pytest.raises(ValidationError):
        Organization.objects.create(name="Acme", slug=slug)


def test_a_cleared_slug_is_regenerated_on_save_with_update_fields(db):
    organization = Organization.objects.create(name="Acme")
    organization.slug = ""
    organization.save(update_fields=["name"])
    organization.refresh_from_db()
    assert organization.slug == "acme"


def test_save_retries_when_another_organization_takes_the_slug_first(db, monkeypatch):
    # Stands in for an organization inserted between full_clean() checking the
    # slug was free and this one's insert.
    Organization.objects.create(name="Acme")
    slugs = iter(["acme", "acme-2"])
    monkeypatch.setattr(Organization, "validate_unique", lambda self, exclude=None: None)
    monkeypatch.setattr(Organization, "_generate_slug", lambda self: next(slugs))

    organization = Organization.objects.create(name="Acme")

    assert organization.slug == "acme-2"


def test_save_gives_up_after_the_retry_limit(db, monkeypatch):
    Organization.objects.create(name="Acme")
    monkeypatch.setattr(Organization, "validate_unique", lambda self, exclude=None: None)
    monkeypatch.setattr(Organization, "_generate_slug", lambda self: "acme")

    with pytest.raises(IntegrityError):
        Organization.objects.create(name="Acme")


def test_save_does_not_retry_an_integrity_error_unrelated_to_the_slug(db, monkeypatch):
    other = Organization.objects.create(name="Acme")
    other.get_or_create_embed_token()
    generated = []
    original = Organization._generate_slug
    monkeypatch.setattr(Organization, "validate_unique", lambda self, exclude=None: None)
    monkeypatch.setattr(Organization, "_generate_slug", lambda self: generated.append(1) or original(self))

    with pytest.raises(IntegrityError):
        Organization.objects.create(name="Globex", embed_token=other.embed_token)

    assert len(generated) == 1


def test_public_url_uses_the_slug(db, settings):
    organization = Organization.objects.create(name="Acme")
    base_url = settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]
    assert organization.public_url == f"{base_url}/email_learning/public/@acme/"


def test_public_url_is_none_for_a_private_organization(db):
    assert Organization.objects.create(name="Acme", is_public=False).public_url is None


def test_public_url_uses_the_host_route_named_in_settings(db, settings):
    organization = Organization.objects.create(name="Acme")
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "PUBLIC_URL_NAMES": {"organization": "root_organization_page"},
    }
    base_url = settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]
    assert organization.public_url == f"{base_url}/@acme/"
