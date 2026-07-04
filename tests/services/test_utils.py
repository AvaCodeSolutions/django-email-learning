from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage

from django_email_learning.services import utils


def test_get_private_file_storage_defaults_to_filesystem_storage(monkeypatch):
    monkeypatch.setattr(utils, "DJANGO_EMAIL_LEARNING_CONFIGS", {})

    storage = utils.get_private_file_storage()

    assert isinstance(storage, FileSystemStorage)
    assert str(storage.location) == str(utils.BASE_DIR / "private_files")


def test_get_private_file_storage_uses_location_when_set(monkeypatch, tmp_path):
    monkeypatch.setattr(
        utils,
        "DJANGO_EMAIL_LEARNING_CONFIGS",
        {"PRIVATE_FILE_STORAGE_LOCATION": str(tmp_path)},
    )

    storage = utils.get_private_file_storage()

    assert isinstance(storage, FileSystemStorage)
    assert str(storage.location) == str(tmp_path)


def test_get_private_file_storage_uses_storages_alias_when_set(monkeypatch):
    monkeypatch.setattr(
        utils,
        "DJANGO_EMAIL_LEARNING_CONFIGS",
        {"PRIVATE_FILE_STORAGE_ALIAS": "staticfiles"},
    )

    storage = utils.get_private_file_storage()

    assert isinstance(storage, StaticFilesStorage)


def test_get_private_file_storage_alias_takes_precedence_over_location(monkeypatch, tmp_path):
    monkeypatch.setattr(
        utils,
        "DJANGO_EMAIL_LEARNING_CONFIGS",
        {
            "PRIVATE_FILE_STORAGE_ALIAS": "staticfiles",
            "PRIVATE_FILE_STORAGE_LOCATION": str(tmp_path),
        },
    )

    storage = utils.get_private_file_storage()

    assert isinstance(storage, StaticFilesStorage)


def test_get_private_file_storage_raises_for_unknown_alias(monkeypatch):
    monkeypatch.setattr(
        utils,
        "DJANGO_EMAIL_LEARNING_CONFIGS",
        {"PRIVATE_FILE_STORAGE_ALIAS": "does-not-exist"},
    )

    try:
        utils.get_private_file_storage()
        raise AssertionError("Expected an exception for an unknown STORAGES alias.")
    except (ImproperlyConfigured, KeyError):
        pass
