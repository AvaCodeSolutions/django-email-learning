Newsletters
===========

django-email-learning includes a built-in newsletter system. Platform admins can create newsletters per organisation, grow a subscriber list, and schedule email campaigns (sendouts).

Overview
--------

- **Newsletter** — a named mailing list belonging to an organisation with a configured language.
- **Subscriber** — a person who has opted in via the public subscription form or been auto-subscribed through a course enrollment.
- **Sendout** — a scheduled email campaign with a subject, rich-text body, and optional inline images.
- **SendoutDelivery** — a per-subscriber delivery record used to track status and retries independently for each recipient.

Managing newsletters
--------------------

From the platform UI, navigate to an organisation and open the **Newsletters** tab. You can:

- Create and edit newsletters (title, language).
- Link a newsletter to a course — learners who enroll in that course are automatically subscribed.
- View and export the subscriber list as CSV.
- Create, edit, and delete scheduled sendouts.

Public subscription
-------------------

Each organisation has a public page that includes a subscription form for every newsletter that belongs to it. Visitors can subscribe without needing a platform account.

Every email sent to subscribers contains a personalised unsubscribe link. Clicking it unsubscribes the recipient immediately without requiring a login.

Sending newsletters
-------------------

Sendouts are delivered by the ``send_newsletters`` management command (see :doc:`../technical/management-commands`) or the matching HTTP trigger endpoint. The command fan-outs each sendout to all current subscribers, tracks delivery per subscriber, and retries failed deliveries up to the configured limit.

Configuration
-------------

All newsletter settings are nested under ``DJANGO_EMAIL_LEARNING`` in your Django settings:

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        # Sender address for newsletter emails.
        # Falls back to FROM_EMAIL, then "webmaster@localhost".
        "NEWSLETTERS": {
            "FROM_EMAIL": "newsletter@example.com",
            "MAX_RETRIES": 3,       # per-subscriber retry limit (default 3)
            "MAX_SUBSCRIBERS": 500, # subscriber cap per newsletter (default: no limit)
            "SENDOUT_ALLOWED_RESOLVER": "myapp.newsletters.is_sendout_allowed",
            "SENDOUT_BLOCKED_MESSAGE_RESOLVER": "myapp.newsletters.sendout_blocked_message",
        },

        # Optional: replace the default database-backed sendout queue.
        "SENDOUT_QUEUE": "myapp.queues.CustomSendoutQueue",

        # Base URL used to build the unsubscribe link in emails.
        "SITE_BASE_URL": "https://example.com",
    }

``MAX_SUBSCRIBERS`` sets a global cap applied to all newsletters. If you need a different limit per newsletter or per organisation, you can subclass the subscription view and override ``get_max_subscribers()``:

.. code-block:: python

    from django_email_learning.public.views import NewsletterSubscribeView

    class MySubscribeView(NewsletterSubscribeView):
        def get_max_subscribers(self) -> int:
            # e.g. look up a per-newsletter quota from your own model
            return self.newsletter.custom_limit

The same hook exists on the public API subscription view (``django_email_learning.public.api.views``) if you are using the API endpoint instead.

``SENDOUT_ALLOWED_RESOLVER`` is checked once per due sendout, right before it's fanned out to subscribers, and defaults to always-allowed. It's a dotted path to a callable that takes the ``Sendout`` instance and returns a ``bool`` — useful for e.g. capping how many sendouts an organisation can send per period. Each due sendout is checked individually rather than caching the answer per organisation, since one sendout completing can change what should happen for the next one from the same organisation:

.. code-block:: python

    from datetime import timedelta

    from django.utils import timezone

    from django_email_learning.models import Sendout

    MONTHLY_CAP = 5

    def is_sendout_allowed(sendout: Sendout) -> bool:
        organization = sendout.newsletter.organization
        since = timezone.now() - timedelta(days=30)
        sent_this_month = Sendout.objects.filter(
            newsletter__organization=organization,
            status=Sendout.Status.SENT,
            sent_at__gte=since,
        ).count()
        return sent_this_month < MONTHLY_CAP  # or e.g. organization.monthly_sendout_cap

A denial is treated as final rather than retried: a cap that's already hit this poll will almost always still be hit moments later on the next one, so the sendout is moved straight to a terminal **Blocked** state instead of being left **Scheduled** to be re-checked forever. There is currently no automated way to reschedule a blocked sendout from the platform UI — it needs to be re-created, or have its status reset directly.

``SENDOUT_BLOCKED_MESSAGE_RESOLVER`` is an optional companion dotted path to a callable ``(sendout: Sendout) -> str | None``, called once at the moment a sendout is blocked. Its return value is saved to ``Sendout.blocked_message`` and shown in the platform UI (as a tooltip next to the **Blocked** status), so you can explain *why* in your own words — e.g. referencing the specific cap and current usage — rather than the generic fallback message:

.. code-block:: python

    def sendout_blocked_message(sendout: Sendout) -> str:
        return f"Monthly limit of {MONTHLY_CAP} sendouts reached for this organisation."

Because the message is generated and persisted once, at block time, it reflects the state that actually caused the block, even if that state (e.g. the cap usage) has since changed.

Failure handling
----------------

The delivery job tracks each subscriber independently. If a subset of deliveries fail (e.g. due to a bad address), those are retried on subsequent runs up to ``MAX_RETRIES`` times. The sendout is still marked **Sent** as long as at least one subscriber received it (best-effort completion).

If *every* delivery permanently fails — which typically indicates an email configuration problem rather than individual bad addresses — the sendout is kept in **Scheduled** state, all failed deliveries are reset to pending, and a ``sendout_all_deliveries_failed`` metric and ``ERROR`` log entry are emitted so the issue is visible to operators.

If ``SENDOUT_ALLOWED_RESOLVER`` denies a sendout, it's moved to **Blocked** (``blocked_reason="denied_by_resolver"``) and a ``sendout_blocked_by_resolver`` metric and ``WARNING`` log entry are emitted.
