import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from django_email_learning.models import Learner
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE


def test_create_learner(db):
    Learner.objects.create(email="user@example.com", organization_id=1)
    learner = Learner.objects.get(email="user@example.com")
    assert learner.email == "user@example.com"
    assert learner.created_at is not None


def test_learner_create_with_invalid_email(db):
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create(email="invalid-email", organization_id=1)
    assert "Enter a valid email address" in str(exc_info.value)


def test_learner_email_case_insensitivity(db):
    Learner.objects.create(email="USER@EXAMPLE.COM", organization_id=1)
    learner = Learner.objects.get(email="user@example.com", organization_id=1)
    assert learner.email == "user@example.com"


def test_learner_unique_together_email_constraint(db):
    Learner.objects.create(email="user@example.com", organization_id=1)
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create(email="USER@EXAMPLE.COM", organization_id=1)
    assert "Learner with this Organization and Email already exists." in str(exc_info.value)
    learner_count = Learner.objects.filter(email__iexact="user@example.com", organization_id=1).count()
    assert learner_count == 1


def test_learner_email_required(db):
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create()
    assert "This field cannot be blank." in str(exc_info.value)


def test_learner_photo_saved_to_private_storage(db):
    learner = Learner.objects.create(email="user@example.com", organization_id=1)
    learner.photo.save("photo.jpg", ContentFile(b"fake-photo-bytes"))

    assert PRIVATE_FILE_STORAGE.exists(learner.photo.name)

    PRIVATE_FILE_STORAGE.delete(learner.photo.name)


def test_learner_private_photo_url_is_none_without_photo(db):
    learner = Learner.objects.create(email="user@example.com", organization_id=1)
    assert learner.private_photo_url is None


def test_learner_private_photo_url_points_to_private_file_view(db):
    learner = Learner.objects.create(email="user@example.com", organization_id=1)
    learner.photo.save("photo.jpg", ContentFile(b"fake-photo-bytes"))

    url = learner.private_photo_url

    assert url is not None
    assert url.startswith("/email_learning/platform/private_file/?token=")

    PRIVATE_FILE_STORAGE.delete(learner.photo.name)


def test_learner_private_photo_url_falls_back_to_public_storage_for_legacy_photos(db):
    # Simulates a photo saved before Learner.photo moved to private storage:
    # the DB still has the relative path, but the bytes only exist in public
    # storage, since existing files weren't migrated when the field's storage
    # backend changed.
    learner = Learner.objects.create(email="legacy@example.com", organization_id=1)
    legacy_path = "learner_photos/legacy.jpg"
    default_storage.save(legacy_path, ContentFile(b"legacy-photo-bytes"))
    Learner.objects.filter(id=learner.id).update(photo=legacy_path)
    learner.refresh_from_db()

    url = learner.private_photo_url

    assert url == default_storage.url(legacy_path)

    default_storage.delete(legacy_path)


def test_learner_private_photo_url_none_when_file_missing_from_both_storages(db):
    learner = Learner.objects.create(email="missing@example.com", organization_id=1)
    Learner.objects.filter(id=learner.id).update(photo="learner_photos/does-not-exist.jpg")
    learner.refresh_from_db()

    assert learner.private_photo_url is None
