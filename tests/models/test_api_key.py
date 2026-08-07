import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from django_email_learning.models import ApiKey, ApiKeyScope, ApiKeyType
from django_email_learning.models.api_keys import hash_secret


def test_create_platform_key_returns_token_matching_stored_hash(db):
    api_key, token = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")

    assert token.startswith(f"elk_{api_key.key_id}_")
    _, secret = ApiKey.split_token(token)
    assert api_key.matches_secret(secret)
    assert api_key.secret_hash == hash_secret(secret)


def test_stored_key_does_not_contain_the_secret(db):
    _, token = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    _, secret = ApiKey.split_token(token)

    stored = ApiKey.objects.get(name="Ops key")
    assert secret not in stored.secret_hash
    # There is no field anywhere on the row that can be turned back into the token.
    assert not any(secret in str(value) for value in stored.__dict__.values())


def test_split_token_preserves_secrets_containing_the_delimiter(db):
    """The secret is url-safe base64, whose alphabet includes the `_` delimiter,
    so the split has to be bounded rather than greedy."""
    key_id, secret = ApiKey.split_token("elk_abc123_secret_with_underscores")
    assert key_id == "abc123"
    assert secret == "secret_with_underscores"


@pytest.mark.parametrize(
    "token",
    ["", "notatoken", "elk_only-two", "wrongprefix_abc_secret", "elk__secret", "elk_abc_"],
)
def test_split_token_rejects_malformed_tokens(token):
    assert ApiKey.split_token(token) is None


def test_platform_key_cannot_belong_to_an_organization(db):
    with pytest.raises(ValidationError):
        ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Bad key", organization_id=1)


def test_organization_key_requires_an_organization(db):
    with pytest.raises(ValidationError):
        ApiKey.create(
            key_type=ApiKeyType.ORGANIZATION,
            name="Bad key",
            scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
        )


def test_database_constraint_rejects_mismatched_key_type(db):
    """The check constraint is the backstop for writes that bypass clean(),
    so that a platform key can never be produced by omitting a filter."""
    api_key, _ = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Org key",
        organization_id=1,
        scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ApiKey.objects.filter(pk=api_key.pk).update(key_type=ApiKeyType.PLATFORM)


def test_platform_key_rejects_scopes(db):
    with pytest.raises(ValidationError):
        ApiKey.create(
            key_type=ApiKeyType.PLATFORM,
            name="Scoped platform key",
            scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
        )


def test_unknown_scope_is_rejected(db):
    with pytest.raises(ValidationError):
        ApiKey.create(
            key_type=ApiKeyType.ORGANIZATION,
            name="Org key",
            organization_id=1,
            scopes=["courses:destroy"],
        )


def test_revoked_key_is_not_usable(db):
    api_key, _ = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    assert api_key.is_usable

    api_key.revoke()
    assert api_key.is_revoked
    assert not api_key.is_usable


def test_expired_key_is_not_usable(db):
    api_key, _ = ApiKey.create(
        key_type=ApiKeyType.PLATFORM,
        name="Ops key",
        expires_at=timezone.now() - datetime.timedelta(seconds=1),
    )
    assert api_key.is_expired
    assert not api_key.is_usable


def test_future_expiry_is_still_usable(db):
    api_key, _ = ApiKey.create(
        key_type=ApiKeyType.PLATFORM,
        name="Ops key",
        expires_at=timezone.now() + datetime.timedelta(days=1),
    )
    assert not api_key.is_expired
    assert api_key.is_usable


def test_touch_last_used_writes_once_per_resolution_window(db):
    api_key, _ = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")

    api_key.touch_last_used()
    api_key.refresh_from_db()
    first_seen = api_key.last_used_at
    assert first_seen is not None

    # A second call inside the window must not issue another write.
    api_key.touch_last_used()
    api_key.refresh_from_db()
    assert api_key.last_used_at == first_seen


def test_touch_last_used_writes_again_once_stale(db):
    api_key, _ = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    stale = timezone.now() - datetime.timedelta(minutes=5)
    ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=stale)
    api_key.refresh_from_db()

    api_key.touch_last_used()
    api_key.refresh_from_db()
    assert api_key.last_used_at > stale


def test_has_scope(db):
    api_key, _ = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Org key",
        organization_id=1,
        scopes=[ApiKeyScope.ENROLLMENTS_CREATE],
    )
    assert api_key.has_scope(ApiKeyScope.ENROLLMENTS_CREATE)
    assert not api_key.has_scope("something:else")


def test_organization_key_requires_at_least_one_scope(db):
    """A scopeless organization key would authenticate and then be refused by
    every endpoint, so it's rejected at creation rather than issued."""
    with pytest.raises(ValidationError):
        ApiKey.create(key_type=ApiKeyType.ORGANIZATION, name="Scopeless key", organization_id=1)

    with pytest.raises(ValidationError):
        ApiKey.create(key_type=ApiKeyType.ORGANIZATION, name="Scopeless key", organization_id=1, scopes=[])


def test_platform_key_needs_no_scopes(db):
    """The rule is specific to organization keys - platform keys are
    all-or-nothing and must stay scopeless."""
    api_key, _ = ApiKey.create(key_type=ApiKeyType.PLATFORM, name="Ops key")
    assert api_key.scopes == []
