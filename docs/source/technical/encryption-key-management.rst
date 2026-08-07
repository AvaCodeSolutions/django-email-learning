Encryption Key Management
=========================

Django Email Learning encrypts sensitive data at rest — specifically **IMAP passwords** — using `Fernet symmetric encryption <https://cryptography.io/en/latest/fernet/>`_ backed by your ``ENCRYPTION_SECRET_KEY`` setting.

.. note::

   API keys were encrypted this way before 4.0.0. They are now stored as a
   SHA-256 hash instead, which cannot be reversed and therefore needs no
   rotation. Rotating ``ENCRYPTION_SECRET_KEY`` no longer affects them.

This page explains how the encryption works, when and why you might need to rotate the key, and how to do so safely.

How It Works
------------

Every encrypted model row stores its own random ``salt`` alongside the ciphertext.
When the application needs to encrypt or decrypt a value it:

1. Derives a unique Fernet key from ``ENCRYPTION_SECRET_KEY`` + the row's ``salt`` using PBKDF2-HMAC-SHA256 (100 000 iterations).
2. Encrypts (or decrypts) the value with that derived key.

Because each row uses its own salt, a compromise of one row's ciphertext does not allow bulk decryption of other rows.

Models that store encrypted fields:

- ``ImapConnection.password``

When to Rotate the Key
-----------------------

You should rotate ``ENCRYPTION_SECRET_KEY`` if:

- The key has been accidentally exposed (e.g. committed to version control, leaked in logs).
- Your security policy requires periodic key rotation.
- You are migrating to a new environment and want a clean key.

.. warning::

   Changing ``ENCRYPTION_SECRET_KEY`` in settings **without** running the rotation command first will make all existing encrypted data permanently unreadable. Always run ``rotate_encryption_key`` before updating the setting.

Rotating the Key
----------------

The ``rotate_encryption_key`` management command re-encrypts all protected data from the old key to the new key within a single database transaction, so the operation is atomic — either all records are updated or none are.

Step-by-step
~~~~~~~~~~~~

1. **Back up your database.** This is a destructive operation if something goes wrong.

2. **Dry run first** to verify everything decrypts cleanly with the old key:

   .. code-block:: bash

      python manage.py rotate_encryption_key \
          --old-key "your-current-key" \
          --new-key "your-new-key" \
          --dry-run

   The dry run performs all decryption and re-encryption in memory and then rolls back the transaction without writing any changes.

3. **Run the actual rotation:**

   .. code-block:: bash

      python manage.py rotate_encryption_key \
          --old-key "your-current-key" \
          --new-key "your-new-key"

4. **Update your settings** to use the new key:

   .. code-block:: python

      DJANGO_EMAIL_LEARNING = {
          'ENCRYPTION_SECRET_KEY': 'your-new-key',
          # ... other settings
      }

5. **Restart your application** so the new key is picked up.

Command Reference
~~~~~~~~~~~~~~~~~

.. code-block:: text

   python manage.py rotate_encryption_key --old-key OLD --new-key NEW [--dry-run]

Options:

``--old-key OLD``
    The current value of ``ENCRYPTION_SECRET_KEY``. Required.

``--new-key NEW``
    The new key to re-encrypt all data with. Required.

``--dry-run``
    Simulate the rotation without writing any changes. Useful for verifying
    that all records decrypt correctly before committing.

Generating a Strong Key
-----------------------

Use Python to generate a cryptographically secure random key:

.. code-block:: python

   import secrets
   print(secrets.token_urlsafe(64))

The resulting string (86+ characters) is suitable for use as ``ENCRYPTION_SECRET_KEY``.

.. warning::

   Never reuse your Django ``SECRET_KEY`` or your ``JWT_SECRET_KEY`` as the ``ENCRYPTION_SECRET_KEY``.
   Each key should be independent so that a compromise of one does not affect the others.

Security Considerations
-----------------------

- **Store the key securely.** Use environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) rather than hardcoding the key in ``settings.py``.
- **Do not log the key.** Ensure your logging configuration does not capture the ``--old-key`` or ``--new-key`` arguments.
- **Limit access.** Only trusted administrators should be able to run ``rotate_encryption_key``.
- **Audit the rotation.** Record when and by whom the key was rotated in your change log or audit trail.
