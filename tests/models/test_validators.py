import pytest
from django.core.exceptions import ValidationError

from django_email_learning.models.validators import (
    MAX_ORGANIZATION_NAME_LENGTH,
    validate_organization_name,
    validate_safe_name,
)


@pytest.mark.parametrize(
    "value",
    [
        "Acme Consulting",
        "Café Météo, Inc.",
        "日本語",
        "한국어 강의",
        "Introduction to Python",
        "Node.js Fundamentals",
        "Vue.js & Nuxt",
        "Ph.D. Prep Course",
        "J.R.R. Tolkien Studies",
        "C++ for Beginners",
        "Q&A: Sales 101",
        # bare domains and www. hosts are allowed - only http(s):// is rejected
        "evil.com",
        "promo at www.example.com",
        "mail me at admin@example.com",
        "",
    ],
)
def test_validate_safe_name_accepts_ordinary_names(value):
    validate_safe_name(value)  # does not raise


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("Visit http://evil.example", "url_in_name"),
        ("https://evil.example/pwn", "url_in_name"),
        # fullwidth characters normalise to an ASCII URL
        ("ｈｔｔｐ://evil.example", "url_in_name"),
        ("line one\nline two", "control_characters"),
        ("tab\there", "control_characters"),
        ("paragraph\u2029break", "control_characters"),
        ("hidden\u200bword", "hidden_characters"),
        ("bidi\u202eoverride", "hidden_characters"),
        ("isolate\u2066text\u2069", "hidden_characters"),
        # Latin word with a Cyrillic look-alike "а"
        ("Acаdemy", "mixed_scripts"),
        ("Παν日", "mixed_scripts"),
    ],
)
def test_validate_safe_name_rejects_unsafe_names(value, code):
    with pytest.raises(ValidationError) as exc:
        validate_safe_name(value)
    assert exc.value.code == code


def test_validate_safe_name_allows_latin_mixed_with_one_cjk_script():
    validate_safe_name("Python 入門")  # Latin + Han is fine


def test_validate_organization_name_enforces_length_limit():
    validate_organization_name("a" * MAX_ORGANIZATION_NAME_LENGTH)
    with pytest.raises(ValidationError) as exc:
        validate_organization_name("a" * (MAX_ORGANIZATION_NAME_LENGTH + 1))
    assert exc.value.code == "max_length"


def test_validate_organization_name_also_runs_the_safe_name_checks():
    with pytest.raises(ValidationError) as exc:
        validate_organization_name("Spam https://spam.example")
    assert exc.value.code == "url_in_name"
