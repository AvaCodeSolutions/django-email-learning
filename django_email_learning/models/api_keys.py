import datetime
import hashlib
import hmac
import secrets

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .organizations import Organization

User = get_user_model()

TOKEN_PREFIX = "elk"
KEY_ID_BYTES = 12
SECRET_BYTES = 32

# How stale `last_used_at` is allowed to get before a successful authentication
# writes it back. Without this every authenticated request would issue a write
# purely to record activity, which on a hot endpoint costs far more than the
# resolution of the value is worth.
LAST_USED_RESOLUTION_SECONDS = 60


class ApiKeyType(models.TextChoices):
    PLATFORM = "platform", "Platform"
    ORGANIZATION = "organization", "Organization"


class ApiKeyScope(models.TextChoices):
    """Permissions an organization key can carry.

    Deliberately coarse: a scope names a resource and an action, not an
    endpoint, so adding an endpoint to an existing resource doesn't strand
    callers on a key that predates it.
    """

    ENROLLMENTS_CREATE = "enrollments:create", "Create enrollments"


def hash_secret(secret: str) -> str:
    """Hashes the secret half of a token for storage and lookup.

    Plain SHA-256 rather than a password hash: the secret is 256 bits from
    `secrets.token_urlsafe`, so there is no dictionary to attack and the
    stretching a slow KDF buys would only add latency to every authenticated
    request.
    """
    return hashlib.sha256(secret.encode()).hexdigest()


class ApiKey(models.Model):
    """A bearer credential for the machine-facing APIs.

    Two kinds share this table, told apart by `key_type` rather than by
    inferring it from `organization` being null. The distinction matters:
    a platform key can trigger deployment-wide jobs, so "which kind is this?"
    must be an assertion a caller has to satisfy positively, not a property
    that a dropped filter can accidentally produce.

    Only a hash of the secret is stored. The full token is returned once, at
    creation, and cannot be recovered afterwards.
    """

    key_type = models.CharField(max_length=20, choices=ApiKeyType.choices, db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_keys",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    # Public half of the token: identifies the row so verification is a single
    # indexed lookup, and is safe to display in the UI and write to logs.
    key_id = models.CharField(max_length=32, unique=True, editable=False)
    secret_hash = models.CharField(max_length=64, unique=True, editable=False)
    scopes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(key_type=ApiKeyType.PLATFORM, organization__isnull=True)
                | models.Q(key_type=ApiKeyType.ORGANIZATION, organization__isnull=False),
                name="api_key_organization_matches_key_type",
            )
        ]

    def __str__(self) -> str:
        scope = self.organization.name if self.organization else "platform"
        return f"{self.name} ({scope})"

    @staticmethod
    def generate_key_id() -> str:
        # Hex, not url-safe base64: `_` is the token's delimiter, and the
        # base64 alphabet includes it, which would make the split ambiguous.
        return secrets.token_hex(KEY_ID_BYTES)

    @staticmethod
    def generate_secret() -> str:
        return secrets.token_urlsafe(SECRET_BYTES)

    @classmethod
    def build_token(cls, key_id: str, secret: str) -> str:
        return f"{TOKEN_PREFIX}_{key_id}_{secret}"

    @classmethod
    def split_token(cls, token: str) -> tuple[str, str] | None:
        """Splits a token into its (key_id, secret) halves.

        Returns None for anything that isn't in this format, which the caller
        should treat as "not one of our tokens" rather than as invalid — legacy
        JWT credentials still reach the same authentication path.
        """
        # maxsplit=2 keeps the secret intact: it is url-safe base64, so it may
        # legitimately contain the delimiter. key_id is hex and cannot.
        parts = token.split("_", 2)
        if len(parts) != 3 or parts[0] != TOKEN_PREFIX or not parts[1] or not parts[2]:
            return None
        return parts[1], parts[2]

    @classmethod
    def create(
        cls,
        *,
        key_type: str,
        name: str,
        organization_id: int | None = None,
        scopes: list[str] | None = None,
        created_by: User | None = None,  # type: ignore[valid-type]
        expires_at: datetime.datetime | None = None,
    ) -> tuple["ApiKey", str]:
        """Creates a key and returns it alongside the one-time plaintext token.

        The token is the only point at which the secret exists in a readable
        form; nothing persists it, so a caller that discards it has to issue a
        replacement key.
        """
        secret = cls.generate_secret()
        api_key = cls(
            key_type=key_type,
            name=name,
            organization_id=organization_id,
            scopes=scopes or [],
            created_by=created_by,
            expires_at=expires_at,
            key_id=cls.generate_key_id(),
            secret_hash=hash_secret(secret),
        )
        api_key.save()
        return api_key, cls.build_token(api_key.key_id, secret)

    def clean(self) -> None:
        super().clean()
        if self.key_type == ApiKeyType.PLATFORM and self.organization_id is not None:
            raise ValidationError({"organization": "Platform keys must not belong to an organization."})
        if self.key_type == ApiKeyType.ORGANIZATION and self.organization_id is None:
            raise ValidationError({"organization": "Organization keys must belong to an organization."})
        if not isinstance(self.scopes, list) or any(not isinstance(scope, str) for scope in self.scopes):
            raise ValidationError({"scopes": "Scopes must be a list of strings."})
        # Platform keys are all-or-nothing by design: they gate deployment-wide
        # operations that aren't modelled as organization resources, so there is
        # nothing for a scope to narrow them to.
        if self.key_type == ApiKeyType.PLATFORM and self.scopes:
            raise ValidationError({"scopes": "Platform keys do not take scopes."})
        # Every organization endpoint requires a scope, so a scopeless key is a
        # credential that authenticates and can then do nothing. Rejecting it at
        # creation beats handing someone a key that 403s on every call.
        if self.key_type == ApiKeyType.ORGANIZATION and not self.scopes:
            raise ValidationError({"scopes": "Organization keys must carry at least one scope."})
        invalid_scopes = set(self.scopes) - set(ApiKeyScope.values)
        if invalid_scopes:
            raise ValidationError({"scopes": f"Unknown scopes: {', '.join(sorted(invalid_scopes))}."})

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_usable(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def matches_secret(self, secret: str) -> bool:
        return hmac.compare_digest(self.secret_hash, hash_secret(secret))

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])

    def touch_last_used(self) -> None:
        """Records that the key authenticated a request, at minute resolution.

        Written with `update()` rather than `save()` so recording activity can
        never fail a request that has already authenticated — a full_clean()
        here would surface unrelated validation errors from a stale row.
        """
        now = timezone.now()
        if self.last_used_at is not None and (now - self.last_used_at).total_seconds() < LAST_USED_RESOLUTION_SECONDS:
            return
        ApiKey.objects.filter(pk=self.pk).update(last_used_at=now)
        self.last_used_at = now
