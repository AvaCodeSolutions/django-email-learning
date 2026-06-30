import base64
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


class EncryptionMixin(models.Model):
    salt = models.CharField(max_length=32, editable=False)

    @classmethod
    def _fernet(cls, salt: str) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
        try:
            secret = DJANGO_EMAIL_LEARNING_SETTINGS["ENCRYPTION_SECRET_KEY"]
        except KeyError:
            raise ImproperlyConfigured("DJANGO_EMAIL_LEARNING['ENCRYPTION_SECRET_KEY'] must be set in settings.py")
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return Fernet(key)

    @classmethod
    def encrypted_value(cls, value: str, salt: str) -> str:
        f = cls._fernet(salt)
        return f.encrypt(value.encode()).decode()

    def _encrypt_password(self, password: str) -> str:
        if not self.salt:
            self.salt = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
        f = self._fernet(self.salt)
        return f.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        f = self._fernet(self.salt)
        return f.decrypt(encrypted_password.encode()).decode()

    class Meta:
        abstract = True
