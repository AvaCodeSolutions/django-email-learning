from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage

DJANGO_EMAIL_LEARNING_CONFIGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


def mask_email(email_address: str) -> str:
    """Mask email address for logging privacy."""
    try:
        username, domain = email_address.split("@")
        masked_username = username[0] + "***"
        return f"{masked_username}@{domain}"
    except ValueError:
        return "***@***"


BASE_DIR = Path(__file__).resolve().parent.parent


def get_private_file_storage() -> FileSystemStorage:
    return FileSystemStorage(
        location=DJANGO_EMAIL_LEARNING_CONFIGS.get("PRIVATE_FILE_STORAGE_LOCATION", f"{BASE_DIR}/private_files/")
    )


PRIVATE_FILE_STORAGE = FileSystemStorage(
    location=DJANGO_EMAIL_LEARNING_CONFIGS.get("PRIVATE_FILE_STORAGE_LOCATION", f"{BASE_DIR}/private_files/")
)
