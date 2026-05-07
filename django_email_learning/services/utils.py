from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.conf import settings


DJNAGO_EMAIL_LEARNING_CONFIGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


def mask_email(email_address: str) -> str:
    """Mask email address for logging privacy."""
    try:
        username, domain = email_address.split("@")
        masked_username = username[0] + "***"
        return f"{masked_username}@{domain}"
    except ValueError:
        return "***@***"


BASE_DIR = Path(__file__).resolve().parent.parent

PRIVATE_FILE_STORAGE = FileSystemStorage(
    location=DJNAGO_EMAIL_LEARNING_CONFIGS.get(
        "PRIVATE_FILE_STORAGE_LOCATION", f"{BASE_DIR}/private_files/"
    )
)
