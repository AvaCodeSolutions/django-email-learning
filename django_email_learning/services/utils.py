def mask_email(email_address: str) -> str:
    """Mask email address for logging privacy."""
    try:
        username, domain = email_address.split("@")
        masked_username = username[0] + "***"
        return f"{masked_username}@{domain}"
    except ValueError:
        return "***@***"
