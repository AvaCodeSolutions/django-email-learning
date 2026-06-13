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
