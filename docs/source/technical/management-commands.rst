Management Commands
===================

Django Email Learning provides management commands to handle automated tasks required for course delivery and maintenance.

Available Commands
------------------

The project currently includes the following management commands:

- ``check_imap_connections``
- ``cleanup_job_executions``
- ``deactivate_inactive_enrollments``
- ``deliver_contents``
- ``send_reminders``
- ``send_newsletters``
- ``send_certificate_pdfs``
- ``rotate_encryption_key``

check_imap_connections
----------------------

The ``check_imap_connections`` management command checks IMAP connectivity for courses and processes any valid email commands.

The default IMAP implementation, :class:`ImapInterface <django_email_learning.services.defaults.imap_interface.ImapInterface>`, reads the email subject to determine which action to run. It supports ``enroll``, ``verify``, and ``drop`` commands, where ``drop`` is the unsubscribe flow for a course. For example, a learner can send an email with the subject ``enroll django-email-learning`` to enroll in the ``django-email-learning`` course.

If you want to provide your own IMAP handler, it only needs to be compatible with :class:`ImapInterfaceProtocol <django_email_learning.ports.imap_interface_protocol.ImapInterfaceProtocol>`. In that case, set the import path for your custom interface in the ``DJANGO_EMAIL_LEARNING`` settings dictionary using the ``IMAP_INTERFACE`` key.

Usage
~~~~~

.. code-block:: bash

    python manage.py check_imap_connections

Function
~~~~~~~~

This command:

- Verifies IMAP connections for configured courses
- Executes valid email commands when connections are available


cleanup_job_executions
----------------------

The ``cleanup_job_executions`` management command deletes old completed ``JobExecution`` records so the table does not grow indefinitely.

Usage
~~~~~

.. code-block:: bash

    python manage.py cleanup_job_executions

Function
~~~~~~~~

This command:

- Removes completed job executions older than the configured retention window
- Supports a dry run to preview how many rows would be deleted without deleting them

deactivate_inactive_enrollments
-------------------------------

The ``deactivate_inactive_enrollments`` management command deactivates enrollments that have missed quiz deadlines.

Usage
~~~~~

.. code-block:: bash

    python manage.py deactivate_inactive_enrollments

Function
~~~~~~~~

This command:

- Finds enrollments that have missed their quiz/assignment deadlines
- Deactivates those enrollments automatically


deliver_contents Command
------------------------

The ``deliver_contents`` management command processes and delivers scheduled course content to enrolled learners via email.

Usage
~~~~~

.. code-block:: bash

    python manage.py deliver_contents



If you don't have the option to set a cron job or similar scheduling mechanism on the server, or you prefer to use a third-party service,
you can trigger the command via the provided HTTP endpoint. ``/api/jobs/deliver-contents/``
Ensure that you have the necessary authentication and permissions set up to access this endpoint securely. See :doc:`../platform/api_keys` for more details.


Function
~~~~~~~~

This command:

- Identifies content scheduled for delivery based on enrollment dates and configured delays
- Sends lessons and quizzes to learners at the appropriate time
- Updates delivery status and tracking information

Scheduling Requirement
----------------------

The ``deliver_contents`` command must be executed regularly to ensure timely content delivery. It should be scheduled to run automatically using a task scheduler.

Execution Frequency
-------------------

**Recommended Schedule**: Every 15-60 minutes depending on your course delivery requirements.

**Considerations**:
- More frequent execution provides better delivery timing precision
- Less frequent execution reduces server resource usage
- Consider your learner time zones and expected engagement patterns

send_reminders
--------------

The ``send_reminders`` management command runs the reminder job to process scheduled reminders for learners.

Usage
~~~~~

.. code-block:: bash

    python manage.py send_reminders

Function
~~~~~~~~

This command:

- Processes scheduled reminder notifications
- Sends reminders for pending learner actions

send_newsletters
----------------

The ``send_newsletters`` management command delivers scheduled newsletter sendouts to subscribers.

Usage
~~~~~

.. code-block:: bash

    python manage.py send_newsletters

You can also trigger it via HTTP:

.. code-block:: http

    GET /your_preferred_path/api/jobs/send_newsletters/
    Authorization: Bearer <API_KEY>

Function
~~~~~~~~

This command:

- Claims sendouts whose scheduled time has passed
- Fan-outs each sendout to all current subscribers, creating per-subscriber ``SendoutDelivery`` records on first run (so subscribers added after scheduling still receive the email)
- Sends an HTML + plain-text email to each subscriber with a personalised unsubscribe link
- Retries failed deliveries on subsequent runs up to ``NEWSLETTERS.MAX_RETRIES`` (default 3)
- Marks a sendout as **Sent** once at least one delivery succeeds (best-effort)
- Emits a ``sendout_all_deliveries_failed`` metric and an ``ERROR`` log entry if every delivery permanently fails, keeping the sendout in **Scheduled** state for investigation

See :doc:`../platform/newsletters` for configuration options.

send_certificate_pdfs
----------------------

The ``send_certificate_pdfs`` management command emails a PDF certificate to learners whose ``Certificate`` is pending delivery.

Usage
~~~~~

.. code-block:: bash

    python manage.py send_certificate_pdfs

You can also trigger it via HTTP:

.. code-block:: http

    GET /your_preferred_path/api/jobs/send_certificate_pdfs/
    Authorization: Bearer <API_KEY>

Function
~~~~~~~~

This command:

- Claims certificates whose PDF email is still pending
- Renders each certificate as a PDF (requires the ``certificates`` optional dependency group, see :doc:`certificate-pdfs`) and emails it as an attachment
- Retries failures on subsequent runs up to ``CERTIFICATES.MAX_RETRIES`` (default 3), then marks the certificate permanently ``failed``
- Certificates issued before this feature was installed are left alone — see :doc:`certificate-pdfs` for details

See :doc:`certificate-pdfs` for configuration options and the on-demand download endpoint.
