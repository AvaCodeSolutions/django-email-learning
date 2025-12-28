from django_email_learning.models import ImapConnection
from django.core.exceptions import ImproperlyConfigured
import pytest


def test_encrypt_decrypt_password(imap_connection):
    assert not imap_connection.password == "my_secret_password"
    decrypted_password = imap_connection.decrypt_password(imap_connection.password)
    assert decrypted_password == "my_secret_password"


def test_str_representation(imap_connection):
    assert str(imap_connection) == "user@example.com|imap.example.com:993"


@pytest.mark.parametrize("field_name", ["server", "port", "email", "password"])
def test_expected_required_fields(field_name):
    field = ImapConnection._meta.get_field(field_name)
    assert not field.blank
    assert not field.null


@pytest.mark.parametrize("field_name", ["email"])
def test_expected_unique_fields(field_name):
    field = ImapConnection._meta.get_field(field_name)
    assert field.unique


@pytest.mark.parametrize("invalid_server", ["invalid_server", "http://example.com"])
def test_imap_invalid_server_validation(invalid_server, imap_connection):
    imap_connection.server = invalid_server
    with pytest.raises(ValueError):
        imap_connection.full_clean()


@pytest.mark.parametrize(
    "valid_server",
    ["imap.example.com", "127.0.0.1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
)
def test_imap_valid_server_validation(valid_server, imap_connection):
    imap_connection.server = valid_server
    imap_connection.full_clean()  # Should not raise


def test_raise_improperly_configured_if_django_email_learning_config_missing(
    settings, db
):
    delattr(settings, "DJANGO_EMAIL_LEARNING")
    with pytest.raises(ImproperlyConfigured):
        ImapConnection.objects.create(
            server="imap.example.com",
            port=993,
            email="user@example.com",
            password="my_secret_password",
            organization_id=1,
        )


def test_raise_improperly_configured_if_encryption_key_missing(settings, db):
    settings.DJANGO_EMAIL_LEARNING = {}
    with pytest.raises(ImproperlyConfigured):
        ImapConnection.objects.create(
            server="imap.example.com",
            port=993,
            email="user@example.com",
            password="my_secret_password",
            organization_id=1,
        )
