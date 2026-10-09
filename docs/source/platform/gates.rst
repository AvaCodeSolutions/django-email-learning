Gates
=====

A **gate** is a step in a course that holds a learner until something outside the
course happens: a payment clears, an employee account is created, a form is
submitted. Learners who reach a gate wait there. When the gate is **unlocked**,
by your own system through the API or by an admin from the learners page, they
continue with the rest of the course.

Nothing is asked of the learner at a gate. If the gate has a message, it is emailed
to them as they arrive, so they know what is pending, for example with a link to
the payment page.

Adding a Gate
-------------

On the course page, choose **Add → Gate**. A gate has:

**Title**
  What learners wait for, such as *Payment*. Shown to admins, and on the public
  course page next to the lessons the gate locks.

**Key**
  Names the gate in the unlock API, such as ``payment``. Letters, numbers, hyphens
  and underscores; unique within the course. It follows the title until you edit
  it. Changing the key of a gate already in use breaks any integration that still
  sends the old one.

**Message to learners**
  Emailed when a learner reaches the gate. Leave it empty to send nothing.

**Send delay**
  How long after the previous content the learner reaches the gate, like any
  other content.

**Timeout**
  Off by default: learners wait until the gate is unlocked, however long that
  takes. Turn it on to stop waiting after a number of days, counted from when the
  learner reached the gate, and choose what happens then:

  - **Deactivate the enrollment**: the enrollment ends with the reason
    *gate expired*, and the learner is emailed that it has ended and that they can
    enroll again.
  - **Continue past the gate**: the learner moves on as if the gate had been
    unlocked. The unlock is recorded with the source *timeout*.

A gate can be published, unpublished, reordered and moved between tracks like any
other content. An unpublished gate is skipped, so learners pass it without
waiting. A gate cannot route learners onto a track; put it before or after the
content that does.

Waiting Learners
----------------

A learner held at a gate stays **active**: they are still on the course, and can
still be cancelled or unsubscribe. The platform shows them as waiting instead:

- the learners list shows *Waiting at gate: Payment* in place of *Active* when
  filtered to a course, and the status filter has a **Waiting** option;
- the enrollment view shows the gate under the course title, the path marks it as
  waiting, and the timeline records when the learner reached the gate and when it
  was unlocked, and by whom.

Learners waiting at a gate do not count toward the organization's
:ref:`learner cap <learner-capacity>`. They are not taking anything from the course
while they wait, so a course that sells its second half does not use up places on
people who have not paid. A learner with another active enrollment that is not
waiting still counts. Unlocking never checks the cap, so a learner who has paid is
never left stuck because the organization filled up in the meantime.

Unlocking
---------

**From your own system**, call the organization API with a key that carries the
``enrollments:update`` scope. See :ref:`unlock-a-gate`.

**From the platform**, organization admins can open the enrollment and choose
**Unlock** next to the gate. Other roles see the gate but not the button.

Either way, a learner waiting at the gate moves on straight away: the next content
is scheduled with its usual send delay, counted from the unlock, or the enrollment
is completed if the gate was the last content.

A gate can also be unlocked **before** the learner reaches it, through the API. A
payment that clears on day one opens a gate placed after lesson five; the learner
then walks through it without stopping, and gets no gate email. Unlocking is
idempotent: unlocking a gate that is already unlocked changes nothing.

Linking Learners to Your Page
-----------------------------

To get the enrollment id to the page that will unlock the gate, put a **button** in
the gate's message, or in any lesson before it. In the editor, choose
**Insert Button**, give it a text and the page's address, and tick the learner
details to add to the link:

**Enrollment ID**
  The learner's enrollment, which is what the unlock API takes.

**Learner email**
  The learner's email address. Note that it is passed to the page the link opens.

Each detail is added as a query parameter, filled in for each learner as the email
is sent. Its name defaults to the detail's own (``enrollment_id``, ``email``) and
can be changed to whatever the page expects. A Stripe payment link, for example,
takes the enrollment as ``client_reference_id`` and the email as
``prefilled_email``, and Stripe then hands ``client_reference_id`` back in its
``checkout.session.completed`` webhook, ready to pass to the unlock call:

.. code-block:: text

   https://buy.stripe.com/abc123?client_reference_id=1234&prefilled_email=learner%40example.com

A detail that isn't available is left off the link: there is no enrollment when an
admin sends a lesson to themselves, or in a newsletter, whose buttons can only carry
the email.

Reacting in Code
----------------

Two Django signals let a project react to gates in its own code, for example to
start a payment flow when a learner arrives, or to provision an account. Both are
sent with ``sender=Gate``, after the transaction that caused them has committed.

``django_email_learning.signals.gate_reached``
  A learner arrived at a gate they hold no unlock for, and is now waiting.
  Keyword arguments: ``enrollment``, ``course_content`` and ``gate``.

``django_email_learning.signals.gate_unlocked``
  A gate was unlocked for an enrollment, by the API, an admin, or a timeout set to
  continue. Keyword arguments: ``enrollment``, ``course_content``, ``gate``,
  ``unlock`` (the ``GateUnlock`` record, with its ``source``) and ``was_waiting``,
  which is ``False`` when the gate was unlocked before the learner reached it.

.. code-block:: python

   from django.dispatch import receiver

   from django_email_learning.signals import gate_reached


   @receiver(gate_reached)
   def start_checkout(sender, enrollment, gate, **kwargs):
       if gate.key == "payment":
           create_checkout_session(
               email=enrollment.learner.email,
               enrollment_id=enrollment.id,
           )

Pass ``enrollment.id`` to whatever will unlock the gate later. It is the id the
unlock API takes.

The Public Course Page
----------------------

Lessons behind a published gate are listed with a lock in place of the check
mark, and a caption saying what they unlock after, such as *Unlocks after
Payment*. A lesson counts as behind a gate when every way to it passes one: the
gate comes before it on the same track, or the lesson's track is only reached from
content that is itself behind a gate.
