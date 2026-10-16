Enrollment Confirmation and Emails
==================================

A new enrollment starts **unverified** and has to be confirmed before the course
begins. Each course chooses how that happens, and what its learners are emailed on
the way. Both are set on the course page under **Course Info → Edit**, on the
**Enrollment & welcome emails** tab.

Enrollment Confirmation
-----------------------

**Email link** (default)
  The learner is emailed a verification link and confirms the enrollment by
  following it. A course with an IMAP connection also accepts a reply carrying the
  verification code. This is how every course worked before the setting existed.

**Enrollment gate**
  The enrollment waits at an *enrollment gate* until something outside the course
  confirms it, such as a payment clearing or an agreement being signed. Your own
  system confirms it through the API, or an organization admin does from the
  learners page. The learner isn't asked to verify anything, and they get no
  verification link.

The enrollment gate works like a :doc:`gate <gates>` placed in front of the course.
It has a **key** that names it in the same unlock API, so a payment integration that
already unlocks content gates can confirm enrollments with the same call. The key
uses letters, numbers, hyphens and underscores. It must differ from the keys of the
gates inside the course, and the platform refuses a key that clashes either way.

Confirming an Enrollment
~~~~~~~~~~~~~~~~~~~~~~~~

**From your own system**, call the unlock endpoint with the enrollment id and the
enrollment gate's key, using an API key with the ``enrollments:update`` scope (see
:ref:`unlock-a-gate`):

.. code-block:: http

   POST /api/v1/enrollments/1234/unlock/
   Content-Type: application/json

   {
     "gate": "payment"
   }

**From the platform**, an organization admin opens the enrollment on the learners
page. It shows *Waiting at the enrollment gate*, with a **Confirm enrollment** button.
Other roles see the label but not the button.

Either way, the enrollment becomes **active**, its first content is scheduled, the
newsletter subscription chosen at enrollment is confirmed, and the learner is sent
the welcome email. Confirming an enrollment that is already active changes nothing,
so a payment webhook that delivers more than once is safe to pass straight through.
An enrollment that has ended (deactivated) can't be confirmed; the learner has to
enroll again.

While it waits, the learners list shows the enrollment as *Waiting at the enrollment
gate* instead of *Unverified*. Once confirmed, its timeline shows **Enrollment
Confirmed** and how: through the API, or by which admin. See
:doc:`learners` for this and for the open tracking of the enrollment email.

Content gates inside the course can still be unlocked while the enrollment waits to
be confirmed. The learner then passes them without stopping once the course starts.

.. note::

   Some enrollments skip the gate because whoever created them vouches for the
   learner: an admin enrolling a learner from the course page, a Google Groups
   import, and the organization API's create-enrollment call with ``verified: true``
   all start the enrollment **active**. Send ``verified: false`` to have an
   API-created enrollment wait at the gate and receive the enrollment email.

Switching a Course to an Enrollment Gate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Switching only affects how unverified enrollments are confirmed from then on.
Learners who enrolled while the course used email links and haven't verified yet
can no longer use their link. They wait at the enrollment gate like everyone
else, so confirm them through the API or from the learners page. Switching back
to email links doesn't send those learners a new link.

The Emails
----------

The tab has an editor for each email the course sends around confirmation. Each has
its own **subject** and **body**, written in the same editor as lessons, buttons
included. Until you edit one, the course sends the built-in default, in the course's
language. **Restore default** puts it back; the change takes effect when you click
**Update**.

**Enrollment email**
  Sent as soon as a learner enrolls in a course with an enrollment gate, in place of
  the verification email. Use it to tell the learner what their enrollment is
  waiting for, and add a button linking to the page where it happens, such as your
  payment page. Leave the message empty to send nothing.

  The editor appears only while the course uses an enrollment gate. A course
  confirmed by email link always sends the built-in verification email, so the link
  a learner needs can't be edited out of it.

**Welcome email**
  Sent once the enrollment is confirmed, however that happened, just before the
  course starts. Its default is the *Enrollment Verified, Welcome aboard!* email that
  courses sent before it could be edited. The course image is still shown above it,
  and when the learner subscribed to the course's newsletter while enrolling, a line
  letting them unsubscribe is still added below it.

Placeholders
~~~~~~~~~~~~

Type these anywhere in a subject or body, or click one under the editor to insert
it. They are replaced as each email is sent:

``{{ course_title }}``
  The course's title.

``{{ organization_name }}``
  The organization's name.

Buttons
~~~~~~~

Choose **Insert Button** in the editor to add a button. As in lessons and gate
messages, the button's link can carry the learner's **Enrollment ID** and **Learner
email** as query parameters, filled in for each learner as the email is sent. See
:ref:`gates-linking-learners` for how to name the parameters for your page.

A Stripe payment link in the enrollment email, for example, carrying the enrollment
as ``client_reference_id``:

.. code-block:: text

   https://buy.stripe.com/abc123?client_reference_id=1234&prefilled_email=learner%40example.com

Stripe returns ``client_reference_id`` in its ``checkout.session.completed``
webhook. Your webhook handler then passes it to the unlock call above as the
enrollment id, naming the enrollment gate's key.

What Learners See
-----------------

After enrolling on a public course page, or through the embeddable enrollment form,
a learner of a gated course is told that the next steps to complete their enrollment
were emailed to them, rather than being asked to verify their address. The public
enrollment endpoint returns ``"confirmation": "gate"`` (or ``"link"``) alongside
``"status": "enrolled"`` so a custom form can say the same.
