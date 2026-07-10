from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage, storages
from django.urls import reverse

from django_email_learning.services import jwt_service

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


def get_private_file_storage() -> Storage:
    # PRIVATE_FILE_STORAGE_ALIAS, when set, takes precedence and resolves against
    # the project's own STORAGES setting, so private files can use a different
    # backend (e.g. a separate S3 bucket) than public media.
    alias = DJANGO_EMAIL_LEARNING_CONFIGS.get("PRIVATE_FILE_STORAGE_ALIAS")
    if alias:
        return storages[alias]
    return FileSystemStorage(
        location=DJANGO_EMAIL_LEARNING_CONFIGS.get("PRIVATE_FILE_STORAGE_LOCATION", f"{BASE_DIR}/private_files/")
    )


PRIVATE_FILE_STORAGE = get_private_file_storage()


def build_private_file_url(organization_id: int, file_path: str) -> str:
    """
    Builds a signed, time-limited URL to PrivateFileView for a file stored in
    PRIVATE_FILE_STORAGE. Access is re-checked against organization_id when the
    URL is opened, not just at signing time.
    """
    payload = {"org_id": organization_id, "file_path": file_path}
    token = jwt_service.generate_jwt(payload=payload, exp=datetime.now() + timedelta(hours=3))
    return reverse("django_email_learning:platform:private_file_view") + f"?token={token}"
