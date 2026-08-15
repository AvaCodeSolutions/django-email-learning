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


Sending the Next Content Immediately
------------------------------------

Under the course title, the enrollment view shows the learner's next scheduled content delivery — when it is due and which content it is. Organization admins also get a **send now** link next to it.

**send now** delivers that one content straight away, exactly as the delivery job would have when its time arrived: the email is sent, the delivery is recorded against the enrollment, and the course moves on — the next content is scheduled, or the enrollment is completed if that was the last one. Simply editing the schedule's time would not have the same effect, since the delivery job runs on a schedule of its own and the content would still wait for its next run.

A few things worth knowing:

- Only deliveries that are still **scheduled** can be sent this way. A delivery that has already gone out, was canceled, or is blocked shows no link.
- If the delivery job happens to pick up the same delivery at that moment, only one of the two sends it — the other reports that the delivery is no longer scheduled.
- If sending fails, the delivery is retried or blocked by the same rules that apply during a job run, and the dialog reports that the content could not be sent.
- The action is restricted to organization admins. Other roles see the scheduled delivery but no link.


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

The cap only counts distinct learners with at least one **active** enrollment (``EnrollmentStatus.ACTIVE``). Learners with no enrollment, or only unverified, completed, or deactivated enrollments, don't count against it — and a learner active in multiple courses only counts once.

When the cap is reached, new enrollment attempts fail with a 403 response and no ``Learner`` record is created.

Per-organization overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need a different limit per organization (e.g. tiered plans), set ``LEARNERS_CAP_RESOLVER`` to the dotted path of a callable that receives the ``Organization`` instance and returns its cap:

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        "LEARNERS": {
            "LEARNERS_CAP_RESOLVER": "myapp.capacity.get_learners_cap",
        },
        ...
    }

.. code-block:: python

    # myapp/capacity.py
    from django_email_learning.models import Organization

    def get_learners_cap(organization: Organization) -> int:
        # e.g. look up a per-organization quota from your own billing/plan model
        return organization.plan.max_learners

When ``LEARNERS_CAP_RESOLVER`` is set, it takes precedence over ``MAX_LEARNERS_PER_ORGANIZATION`` for every organization.

Checking capacity without enrolling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Organization.can_enroll_learner()`` returns whether the organization currently has room for another learner. It's used to:

- Include a ``can_enroll_learner`` boolean in the platform's organization API responses (``GET``/``POST`` on the organization detail endpoint), so the admin UI can disable the "add learner" action without exposing the actual cap or learner count.
- Include an ``enrollmentOpen`` boolean in the public organization and course page context (``appContext``), so the public enrollment form can disable itself.
