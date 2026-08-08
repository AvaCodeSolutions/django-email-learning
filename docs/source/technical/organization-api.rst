Organization API (v1)
=====================

The organization API lets an organization's own systems act on its data from
outside the platform — enrolling a learner from a partner site's signup flow,
for example, or reconciling enrollment state with an internal CRM.

It is authenticated with an **organization API key**, which an organization
admin issues for themselves. Every request acts on the organization the key
was issued for, and on no other.

.. note::

   This is distinct from the two API surfaces that already existed:

   * :doc:`jobs-api` is authenticated with a *platform* key and triggers
     deployment-wide jobs. Organization keys cannot reach it.
   * ``/api/public/`` is unauthenticated and gated by a publishable embed
     token, for widgets on third-party pages. It is limited to what an
     anonymous visitor may do.

Issuing a Key
-------------

Organization **admins** can create keys for their own organization. Editors,
instructors and viewers cannot: a key acts with whatever scopes it carries, so
issuing one would let a non-admin hand out access it does not itself have.

In the platform UI, open the organization and choose the **API Keys** tab. The
key is shown once, in a dialog, immediately after it is created; the table
afterwards lists each key's id, scopes, status and last use, but never the key
itself.

The tab is shown when the ``organization_api`` platform feature is available,
which it is by default. To hide it, drop
``PlatformFeature.ORGANIZATION_API`` from ``get_available_features()`` on your
platform view:

.. code-block:: python

   class MyOrganizationView(SingleOrganization):
       def get_available_features(self):
           return super().get_available_features() - {PlatformFeature.ORGANIZATION_API}

.. note::

   The flag decides what the UI offers; the permission hooks below decide what
   the API allows. Removing the flag hides the tab, and overriding the hooks
   refuses the operations — set both if you want the feature fully off.

Restricting who may issue keys
------------------------------

``OrganizationApiKeyView`` and ``SingleOrganizationApiKeyView`` each expose a
hook, both defaulting to ``True``. Return ``False`` to reject the request with
a ``403`` before any database work happens — useful for plan limits, a key
quota, or a stricter rule than "organization admin".

.. code-block:: python

   from django_email_learning.platform.api.views import OrganizationApiKeyView


   class LimitedApiKeyView(OrganizationApiKeyView):
       def can_create_organization_api_key(self, request, organization):
           return organization.api_keys.filter(revoked_at__isnull=True).count() < 5

The matching hook for revocation is
``can_delete_organization_api_key(request, organization)`` on
``SingleOrganizationApiKeyView``. Both receive the resolved ``Organization``
rather than its id, so a check can read the organization's own state without a
second query. Route your subclass in place of the shipped view to apply it.

The same thing over HTTP:

.. code-block:: http

   POST /api/platform/organizations/<organization_id>/api-keys/
   Content-Type: application/json

   {
     "name": "Partner signup integration",
     "scopes": ["enrollments:create"],
     "expires_at": "2027-01-01T00:00:00Z"
   }

``name`` and ``scopes`` are required; ``expires_at`` is optional and the key
never expires without it.

The response is the **only** time the token is readable:

.. code-block:: json

   {
     "id": 7,
     "key_id": "a1b2c3d4e5f60718293a4b5c",
     "name": "Partner signup integration",
     "key_type": "organization",
     "organization_id": 3,
     "scopes": ["enrollments:create"],
     "created_at": "2026-08-07T10:00:00Z",
     "created_by": "orgadmin",
     "expires_at": "2027-01-01T00:00:00Z",
     "revoked_at": null,
     "last_used_at": null,
     "token": "elk_a1b2c3d4e5f60718293a4b5c_<secret>"
   }

Only a SHA-256 hash of the secret is stored, so a lost token cannot be
recovered — issue a replacement and revoke the old one. ``key_id`` is the
public half: it identifies the key in the UI, in logs, and when revoking it,
and is not itself a credential.

``GET`` the same URL to list the organization's keys (metadata only, never the
token). ``DELETE /api/platform/organizations/<organization_id>/api-keys/<id>/``
revokes a key; the row is kept so the record of what existed survives.

Scopes
------

.. list-table::
   :header-rows: 1

   * - Scope
     - Grants
   * - ``enrollments:create``
     - Create enrollments

A scope names a resource and an action rather than an endpoint, so adding an
endpoint to an existing resource does not strand callers on a key that predates
it. More scopes will be added as the API grows; a key must carry at least one.

Authentication
--------------

Pass the token as a bearer token:

.. code-block:: http

   Authorization: Bearer elk_<key_id>_<secret>

Failures return ``401`` with an ``error`` message, except for a key that
authenticates but lacks the required scope or is of the wrong type, which
returns ``403``. A revoked or expired key returns ``401``.

Endpoints
---------

Check a key
^^^^^^^^^^^

Requires no scope — any organization key passes, whichever scopes it carries.

.. code-block:: http

   GET /api/v1/ping/

.. code-block:: json

   {
     "status": "ok"
   }

Reads and changes nothing, so it is safe to call as a credential or
connectivity check: a ``200`` means the key authenticates against this
deployment, and a ``401`` or ``403`` means it does not. It is still
authenticated — an unauthenticated probe would say nothing about the key,
which is the thing a caller is checking. It counts against the same per-key
rate limit as everything else.

Create an enrollment
^^^^^^^^^^^^^^^^^^^^

Requires ``enrollments:create``.

.. code-block:: http

   POST /api/v1/enrollments/
   Content-Type: application/json

   {
     "email": "learner@example.com",
     "course_slug": "intro-to-widgets",
     "subscribe_to_newsletter": false
   }

The course is resolved against the key's organization, so a slug belonging to
another organization reads as ``404``. Unlike the embeddable public endpoint,
a course does not need to be public — but it must be enabled.

The learner receives a verification email and the enrollment starts as
``unverified``; it becomes ``active`` once they confirm.

Responses:

* ``201`` — enrolled, with the created enrollment in the body
* ``200`` ``{"status": "already_enrolled"}`` — a non-deactivated enrollment already exists
* ``403`` — the email is blocked, or the organization is at its learner cap
* ``404`` — no such enabled course in this organization

Creating an enrollment is the only endpoint in v1 that acts on data. Read
endpoints for enrollments and courses will follow, each behind its own scope.

OpenAPI Schema
--------------

.. code-block:: http

   GET /api/v1/openapi.json

Returns an OpenAPI 3.1 document for this API, suitable for feeding to Swagger
UI, Redoc, or a client generator. It needs no API key: it describes the shape
of the API and carries no organization data.

The document is generated from the code that serves the API rather than
maintained alongside it — paths come from the URLconf, request and response
schemas from the Pydantic models the views validate with, and the security
requirements from the scopes the authentication decorator enforces. A test
fails the build if a routed endpoint has no documentation, so the two cannot
drift apart.

The document's title defaults to ``Django Email Learning — Organization API``.
A deployment serving the API under its own product name can replace it:

.. code-block:: python

   DJANGO_EMAIL_LEARNING = {
       "OPENAPI": {
           "TITLE": "Acme Learning API",
       },
   }

To stop serving it:

.. code-block:: python

   DJANGO_EMAIL_LEARNING = {
       "ORGANIZATION_API_DOCS_ENABLED": False,
   }

Rate Limiting
-------------

Requests are budgeted per key (by ``key_id``, not by client IP, since a
server-to-server caller may sit behind a shared egress address). Exceeding the
budget returns ``429``. Defaults are 120 requests per 60 seconds; override them
in settings:

.. code-block:: python

   DJANGO_EMAIL_LEARNING = {
       "ORGANIZATION_API_RATE_LIMITS": {
           "PER_KEY_LIMIT": 120,
           "PER_KEY_WINDOW_SECONDS": 60,
       },
   }

Rate limiting is backed by Django's cache framework. A per-process
``LocMemCache`` under-counts across worker processes, so a shared backend such
as Redis is recommended in production.
