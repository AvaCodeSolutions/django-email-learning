from django.db import models
from .organizations import Organization
from .mixin_models import EncryptionMixin
from cryptography.fernet import InvalidToken
import ipaddress
import re


def is_domain_or_ip(value: str) -> None:
    """
    Validate if the given value is a valid domain name or IP address.

    Raises:
        ValueError: If the value is not a valid domain or IP address.
    """
    try:
        ipaddress.ip_address(value)
    except ValueError:
        DOMAIN_REGEX = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$")
        if not bool(DOMAIN_REGEX.match(value.lower())):
            raise ValueError(f"{value} is not a valid domain or IP address")


class ImapConnection(EncryptionMixin):
    server = models.CharField(max_length=200, validators=[is_domain_or_ip])
    port = models.IntegerField(db_default=993)
    email = models.EmailField(max_length=200, unique=True)
    password = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.email}|{self.server}:{self.port}"

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.password:
            try:
                self.decrypt_password(self.password)
                # Password is already encrypted
            except InvalidToken:
                self.password = self._encrypt_password(self.password)
        if self.server:
            self.server = self.server.lower()
        self.full_clean()
        super().save(*args, **kwargs)


class InboxFolder(models.Model):
    imap_connection = models.ForeignKey(
        ImapConnection, on_delete=models.CASCADE, related_name="folders"
    )
    folder_name = models.CharField(max_length=200)

    def __str__(self) -> str:
        return f"{self.imap_connection.email} - {self.folder_name}"
