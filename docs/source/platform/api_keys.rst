API Keys
========

API Keys provide a secure way to authenticate programmatic access to the Django Email Learning platform. They are designed to enable automated job execution without the need to set up cron jobs directly on the server.

Only a SHA-256 hash of each key is stored, so the platform cannot recover a key
once it has been issued. The full key is shown **once**, immediately after
creation — copy it then, or issue a replacement.

.. note::

   The keys described on this page are **platform** keys, which act
   deployment-wide. Organization admins can also issue **organization** keys,
   scoped to a single organization's data — see
   :doc:`../technical/organization-api`.

.. image:: ../../images/api-keys.png
   :alt: API Keys Management Interface
   :align: center

Overview
--------

API Keys allow you to:

* Run scheduled jobs programmatically (e.g., ``deliver_contents``)
* Automate content delivery without server-level cron access
* Manage multiple keys for different automation scenarios
* Track which user created each key for audit purposes

This is particularly useful when:

* You don't have direct server access to configure cron jobs
* You want to trigger jobs from external systems or CI/CD pipelines
* You need to integrate Django Email Learning with other automation tools
* You prefer managing scheduled tasks through external job schedulers

See :doc:`../technical/jobs-api` for the job-trigger endpoints' request/response contract, including asynchronous execution and status polling.

Access Requirements
-------------------

Only **Platform Administrators** can create and manage API keys. This includes:

* Platform Admins (members of the "Platform Admin" group)
* Superusers

Creating an API Key
-------------------

1. Navigate to **Settings** → **API Keys** from the platform navigation menu
2. Click the **Add API Key** button
3. The system generates a secure, random API key and displays it once

Copy the key from that dialog before closing it. It is not stored in a
recoverable form and cannot be shown again.

Managing API Keys
-----------------

The API Keys page displays all existing keys with the following information:

* **Key ID** - The key's public identifier, used to recognise it here and in logs. It is not a credential and cannot be used to authenticate.
* **Status** - Active, Revoked, or Expired
* **Created By** - The username of the administrator who created the key
* **Created At** - Timestamp when the key was created
* **Last Used** - When the key last authenticated a request, or "Never used"
* **Actions** - Revoke button

Revoking a key stops it working immediately. The record is kept rather than
deleted, so the history of which keys existed — and when each was last used —
survives revocation.
