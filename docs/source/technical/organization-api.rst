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

.. note::

   Key management is API-only for now — there is no organization-facing
   settings screen for these keys yet.

.. code-block:: http

   POST /api/platform/organizations/<organization_id>/api-keys/
   Content-Type: application/json

   {
     "name": "Partner signup integration",
     "scopes": ["enrollments:write"],
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
     "scopes": ["enrollments:write"],
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
   * - ``courses:read``
     - List the organization's courses
   * - ``enrollments:read``
     - List the organization's enrollments
   * - ``enrollments:write``
     - Create enrollments

A scope names a resource and an access level rather than an endpoint, so
adding an endpoint to an existing resource does not strand callers on a key
that predates it.

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

Create an enrollment
^^^^^^^^^^^^^^^^^^^^

Requires ``enrollments:write``.

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

List enrollments
^^^^^^^^^^^^^^^^

Requires ``enrollments:read``.

.. code-block:: http

   GET /api/v1/enrollments/?course_slug=intro-to-widgets&status=active&limit=50&offset=0

Optional filters: ``course_slug``, ``email``, ``status`` (one of
``unverified``, ``active``, ``completed``, ``deactivated``). ``limit`` defaults
to 50 and is capped at 200. The response carries ``enrollments``, ``total``,
``limit`` and ``offset``.

List courses
^^^^^^^^^^^^

Requires ``courses:read``.

.. code-block:: http

   GET /api/v1/courses/

Returns every course in the organization, including disabled ones — a caller
needs to see a disabled course to understand why enrolling into it failed.

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
