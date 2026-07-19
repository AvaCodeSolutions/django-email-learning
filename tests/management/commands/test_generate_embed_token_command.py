from io import StringIO

from django.core.management import call_command

from django_email_learning.models import Organization


def test_generates_a_token_for_the_organization(db) -> None:
    organization = Organization.objects.get(id=1)
    assert organization.embed_token is None

    stdout = StringIO()
    call_command("generate_embed_token", organization.id, stdout=stdout)

    organization.refresh_from_db()
    assert organization.embed_token is not None
    assert organization.embed_token in stdout.getvalue()


def test_rotating_overwrites_the_previous_token(db) -> None:
    organization = Organization.objects.get(id=1)
    call_command("generate_embed_token", organization.id, stdout=StringIO())
    organization.refresh_from_db()
    first_token = organization.embed_token

    call_command("generate_embed_token", organization.id, stdout=StringIO())
    organization.refresh_from_db()

    assert organization.embed_token != first_token


def test_reports_error_for_unknown_organization(db) -> None:
    stdout = StringIO()

    call_command("generate_embed_token", 999999, stdout=stdout)

    assert "does not exist" in stdout.getvalue()
