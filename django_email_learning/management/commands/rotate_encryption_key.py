import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandParser, OutputWrapper
from django.db import transaction

from django_email_learning.models import ImapConnection
from django_email_learning.models.mixin_models import EncryptionMixin

logger = logging.getLogger(__name__)


def _re_encrypt(
    model_class: type[EncryptionMixin],
    field: str,
    old_secret: str,
    new_secret: str,
    stdout: OutputWrapper,
    style: Any,
    dry_run: bool,
) -> int:
    """Re-encrypt all rows of a model using the new secret key."""
    updated = 0

    for obj in model_class.objects.all():  # type: ignore[attr-defined]
        encrypted = getattr(obj, field)
        if not encrypted:
            continue
        try:
            # Decrypt with old key
            import base64

            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

            def _fernet(secret: str, salt: str) -> Fernet:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt.encode(),
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
                return Fernet(key)

            plaintext = _fernet(old_secret, obj.salt).decrypt(encrypted.encode()).decode()
            new_encrypted = _fernet(new_secret, obj.salt).encrypt(plaintext.encode()).decode()

            if not dry_run:
                model_class.objects.filter(pk=obj.pk).update(**{field: new_encrypted})  # type: ignore[attr-defined]

            updated += 1
            stdout.write(f"  {'[dry-run] ' if dry_run else ''}Re-encrypted {model_class.__name__} pk={obj.pk}")
        except Exception as e:
            stdout.write(style.ERROR(f"  Failed to re-encrypt {model_class.__name__} pk={obj.pk}: {e}"))
            raise

    return updated


class Command(BaseCommand):
    help = (
        "Re-encrypt all data protected by ENCRYPTION_SECRET_KEY using a new key. "
        "Run this after rotating the key in settings. "
        "Always back up your database before running."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--old-key",
            required=True,
            help="The current (old) ENCRYPTION_SECRET_KEY value.",
        )
        parser.add_argument(
            "--new-key",
            required=True,
            help="The new ENCRYPTION_SECRET_KEY value to encrypt data with.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the rotation without writing any changes to the database.",
        )

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        old_key: str = options["old_key"]
        new_key: str = options["new_key"]
        dry_run: bool = options["dry_run"]

        if old_key == new_key:
            self.stdout.write(self.style.WARNING("Old and new keys are identical — nothing to do."))
            return

        self.stdout.write(self.style.WARNING("WARNING: Ensure you have a database backup before proceeding."))
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode — no changes will be written."))

        # Models and their encrypted field. ApiKey used to appear here; it now
        # stores only a hash of its secret, which by definition cannot be
        # re-encrypted under a new key and needs no rotation.
        targets: list[tuple[type[EncryptionMixin], str]] = [
            (ImapConnection, "password"),
        ]

        total = 0
        try:
            with transaction.atomic():
                for model_class, field in targets:
                    self.stdout.write(f"\nProcessing {model_class.__name__}.{field}...")
                    count = _re_encrypt(
                        model_class=model_class,
                        field=field,
                        old_secret=old_key,
                        new_secret=new_key,
                        stdout=self.stdout,
                        style=self.style,
                        dry_run=dry_run,
                    )
                    self.stdout.write(f"  → {count} record(s) processed.")
                    total += count

                if dry_run:
                    raise _DryRunRollback()

        except _DryRunRollback:
            self.stdout.write(
                self.style.WARNING(f"\nDry run complete. {total} record(s) would be updated. No changes written.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\nRotation complete. {total} record(s) re-encrypted.\n"
                "Next step: update ENCRYPTION_SECRET_KEY in your settings to the new key."
            )
        )


class _DryRunRollback(Exception):
    """Raised to roll back the transaction in dry-run mode."""
