Management Commands
===================

Django Email Learning provides management commands to handle automated tasks required for course delivery and maintenance.

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
