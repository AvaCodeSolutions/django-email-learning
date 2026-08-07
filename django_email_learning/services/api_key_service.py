"""Authentication for the machine-facing APIs.

Verification is a single indexed lookup on the token's public `key_id` half
followed by a constant-time comparison of the hashed secret half. Credentials
issued before 3.1.0 are JWTs carrying the raw key, and are resolved through the
same hash so both formats converge on one code path.
"""

import hmac
import typing

from django_email_learning.models import ApiKey
from django_email_learning.models.api_keys import hash_secret
from django_email_learning.services.jwt_service import (
    ExpiredTokenException,
    InvalidTokenException,
    decode_jwt,
)

INVALID_KEY_MESSAGE = "Invalid API key"

# Compared against when no row matches, so that a lookup miss costs the same as
# a wrong secret and can't be distinguished by how long the response took.
_DUMMY_HASH = hash_secret("dummy-secret-for-constant-time-comparison")


class ApiKeyAuthenticationError(Exception):
    """Carries the response a failed authentication should produce.

    Messages are deliberately uniform for every "we couldn't resolve this to a
    key" case: distinguishing an unknown key_id from a bad secret would let a
    caller confirm which key ids exist.
    """

    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def extract_bearer_token(request: typing.Any) -> str:
    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        raise ApiKeyAuthenticationError("Authorization header missing")
    parts = authorization_header.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise ApiKeyAuthenticationError("Invalid Authorization header format. Expected: Bearer <API_KEY>")
    return parts[1]


def _authenticate_legacy_jwt(token: str) -> ApiKey:
    """Resolves a pre-3.1.0 JWT credential.

    The JWT never added anything a bearer token doesn't already have — it was
    signed with a fixed `exp` of `datetime.max` and its only real payload was
    the salt needed to narrow the old decrypt-and-compare lookup. It is
    accepted here purely so existing deployments don't break on upgrade.
    """
    try:
        payload = decode_jwt(token)
    except ExpiredTokenException:
        raise ApiKeyAuthenticationError("Expired Json Web Token")
    except InvalidTokenException:
        raise ApiKeyAuthenticationError("Invalid Json Web Token")

    if "key" not in payload or "salt" not in payload:
        raise ApiKeyAuthenticationError("Json Web Token missing required fields")

    api_key = ApiKey.objects.select_related("organization").filter(secret_hash=hash_secret(payload["key"])).first()
    if api_key is None:
        raise ApiKeyAuthenticationError(INVALID_KEY_MESSAGE)
    return api_key


def authenticate_token(token: str) -> ApiKey:
    """Resolves a bearer token to a usable ApiKey, or raises.

    Anything that isn't in the `elk_<key_id>_<secret>` shape falls through to
    the legacy JWT path rather than being rejected outright.
    """
    split = ApiKey.split_token(token)
    if split is None:
        api_key = _authenticate_legacy_jwt(token)
    else:
        key_id, secret = split
        candidate = ApiKey.objects.select_related("organization").filter(key_id=key_id).first()
        if candidate is None:
            # Hash anyway, so a lookup miss costs the same as a wrong secret.
            hmac.compare_digest(_DUMMY_HASH, hash_secret(secret))
            raise ApiKeyAuthenticationError(INVALID_KEY_MESSAGE)
        if not candidate.matches_secret(secret):
            raise ApiKeyAuthenticationError(INVALID_KEY_MESSAGE)
        api_key = candidate

    # Only reported once the caller has proved possession of the secret, so
    # neither message tells an attacker anything they didn't already hold.
    if api_key.is_revoked:
        raise ApiKeyAuthenticationError("API key has been revoked")
    if api_key.is_expired:
        raise ApiKeyAuthenticationError("API key has expired")

    api_key.touch_last_used()
    return api_key
