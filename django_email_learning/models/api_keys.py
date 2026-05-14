from cryptography.fernet import InvalidToken
from django.db import models
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model
from .mixin_models import EncryptionMixin
import base64
import uuid

User = get_user_model()


class ApiKey(EncryptionMixin):
    key = models.CharField(
        max_length=256, unique=True, validators=[MinLengthValidator(50)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    @classmethod
    def generate_key(cls) -> str:
        return (
            base64.urlsafe_b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)
            .decode()
            .rstrip("=")
        )

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        try:
            self.decrypt_password(self.key)
            # Key is already encrypted
        except InvalidToken:
            self.key = self._encrypt_password(self.key)
        self.full_clean()
        super().save(*args, **kwargs)
