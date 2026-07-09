Learner Management
==================

Overview
--------

The learners section is accessible to users with appropriate permissions and allows you to:

- View all learners enrolled in your organization's courses
- Search and filter learners by email
- Monitor individual progress and performance


Learner Discovery
-----------------

**Search Functionality**
  Use the search bar to quickly find learners by email address. This is particularly useful for large organizations with many enrolled learners.


Individual Learner Details
--------------------------

Clicking on any learner's email address opens a detailed view providing comprehensive information about their learning journey.


**Course-Specific Progress**
  For each enrolled course, you can access:
  - **Content Progress**: Which lessons have been delivered and viewed
  - **Quiz Performance**: Scores, attempts, and completion status
  - **Timeline View**: Chronological learning activity

.. image:: ../../images/learner-progress.png
   :alt: Learner Management Interface
   :align: center


Learner Capacity
-----------------

You can cap the number of learners an organization is allowed to enroll. This applies across every enrollment path — the platform UI, the public enrollment page, Google Workspace group enrollment, and IMAP-based enrollment.

Configuration
~~~~~~~~~~~~~

The cap is nested under ``DJANGO_EMAIL_LEARNING`` in your Django settings:

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        "LEARNERS": {
            "MAX_LEARNERS_PER_ORGANIZATION": 500,  # default: 0 (unlimited)
        },
        ...
    }

``MAX_LEARNERS_PER_ORGANIZATION`` sets a global cap applied to every organization. A value of ``0`` (the default) means unlimited. A learner who is already enrolled somewhere in the organization is never blocked by the cap — it only applies when a *new* learner would be created.

When the cap is reached, new enrollment attempts fail with a 403 response and no ``Learner`` record is created.

Per-organization overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need a different limit per organization (e.g. tiered plans), override ``get_learners_cap()`` on a custom ``Organization`` subclass:

.. code-block:: python

    from django_email_learning.models import Organization

    class MyOrganization(Organization):
        class Meta:
            proxy = True

        def get_learners_cap(self) -> int:
            # e.g. look up a per-organization quota from your own billing/plan model
            return self.plan.max_learners

Checking capacity without enrolling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Organization.can_enroll_learner()`` returns whether the organization currently has room for another learner. It's used to:

- Include a ``can_enroll_learner`` boolean in the platform's organization API responses (``GET``/``POST`` on the organization detail endpoint), so the admin UI can disable the "add learner" action without exposing the actual cap or learner count.
- Include an ``enrollmentOpen`` boolean in the public organization and course page context (``appContext``), so the public enrollment form can disable itself.
