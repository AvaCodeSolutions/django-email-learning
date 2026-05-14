import pytest
from django_email_learning.models import BlockedEmail
from django.core.exceptions import ValidationError


def test_invalid_email_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        BlockedEmail.objects.create(email="email")
    assert "Enter a valid email address." in str(exc_info.value)


def test_email_is_lowercased_on_save(db):
    blocked_email = BlockedEmail.objects.create(email="TEST@EXAMPLE.COM")
    assert blocked_email.email == "test@example.com"


def test_str_representation(blocked_email):
    assert str(blocked_email) == "blacklisted@email.com"


def test_unique_email_constraint(blocked_email):
    with pytest.raises(ValidationError) as exc_info:
        BlockedEmail.objects.create(email="blacklisted@email.com")
    assert "Email already exists." in str(exc_info.value)
