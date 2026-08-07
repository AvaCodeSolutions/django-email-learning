import base64
import hashlib
import secrets
import sys

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.db import migrations


def _fernet(salt: str) -> Fernet:
    """Reimplements EncryptionMixin._fernet as it stood before this release.

    Inlined rather than imported: the model method is removed by 0019, and a
    data migration must keep working against the code of its own era rather
    than whatever the model looks like today.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=100000,
    )
    secret = str(settings.DJANGO_EMAIL_LEARNING["ENCRYPTION_SECRET_KEY"])
    return Fernet(base64.urlsafe_b64encode(kdf.derive(secret.encode())))


def backfill(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
    """Derives key_id/secret_hash for existing keys from the encrypted column.

    Existing credentials keep working: the pre-3.1 JWT carries the raw key, and
    the new authentication path hashes whatever it extracts from that JWT into
    the same `secret_hash` written here.

    A key whose ciphertext won't decrypt — the usual cause is a rotated
    ENCRYPTION_SECRET_KEY — gets a random hash no token can ever match, so the
    row survives the non-null constraint in 0019 while failing closed. The
    alternative, deleting it, would silently widen access if that key was the
    only thing gating an endpoint.
    """
    ApiKey = apps.get_model("django_email_learning", "ApiKey")
    undecryptable = []

    for api_key in ApiKey.objects.all():
        try:
            plaintext = _fernet(api_key.salt).decrypt(api_key.key.encode()).decode()
            secret_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        except (InvalidToken, ValueError, TypeError):
            undecryptable.append(api_key.pk)
            secret_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()

        api_key.key_type = "platform"
        api_key.key_id = secrets.token_hex(12)
        api_key.secret_hash = secret_hash
        api_key.name = f"Legacy platform key #{api_key.pk}"
        api_key.scopes = []
        api_key.save(update_fields=["key_type", "key_id", "secret_hash", "name", "scopes"])

    if undecryptable:
        print(
            f"\n  WARNING: {len(undecryptable)} API key(s) could not be decrypted "
            f"(ids: {', '.join(str(pk) for pk in undecryptable)}). They have been "
            f"left in place but can no longer authenticate; issue replacements.",
            file=sys.stderr,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("django_email_learning", "0017_apikey_add_type_and_hashed_storage"),
    ]

    # Irreversible in substance rather than in form: 0019 drops the plaintext
    # source, and a hash cannot be turned back into the key it came from.
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
