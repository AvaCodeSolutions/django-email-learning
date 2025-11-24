from django.core.exceptions import ValidationError
from django_email_learning.models import Learner
import pytest


def test_create_learner(db):
    Learner.objects.create(email="user@example.com")
    learner = Learner.objects.get(email="user@example.com")
    assert learner.email == "user@example.com"
    assert learner.created_at is not None


def test_learner_create_with_invalid_email(db):
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create(email="invalid-email")
    assert "Enter a valid email address" in str(exc_info.value)


def test_learner_email_case_insensitivity(db):
    Learner.objects.create(email="USER@EXAMPLE.COM")
    learner = Learner.objects.get(email="user@example.com")
    assert learner.email == "user@example.com"


def test_learner_unique_email_constraint(db):
    Learner.objects.create(email="user@example.com")
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create(email="USER@EXAMPLE.COM")
    assert "Learner with this Email already exists." in str(exc_info.value)
    learner_count = Learner.objects.filter(email__iexact="user@example.com").count()
    assert learner_count == 1


def test_learner_email_required(db):
    with pytest.raises(ValidationError) as exc_info:
        Learner.objects.create()
    assert "This field cannot be blank." in str(exc_info.value)
