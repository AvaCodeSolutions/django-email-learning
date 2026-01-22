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

Function
~~~~~~~~

This command:

- Identifies content scheduled for delivery based on enrollment dates and configured delays
- Sends lessons and quizzes to learners at the appropriate time
- Updates delivery status and tracking information

Scheduling Requirement
----------------------

The ``deliver_contents`` command must be executed regularly to ensure timely content delivery. It should be scheduled to run automatically using a task scheduler.

.. note::
    The current version does not have an endpoint to trigger this command, so for this MVP version, you will need to set up a cron job or similar scheduling mechanism manually.
    For future versions, we plan to introduce an HTTP endpoint to trigger this command. which can be used by webhooks or other services to initiate content delivery without relying solely on cron jobs.

Execution Frequency
-------------------

**Recommended Schedule**: Every 15-60 minutes depending on your course delivery requirements.

**Considerations**:
- More frequent execution provides better delivery timing precision
- Less frequent execution reduces server resource usage
- Consider your learner time zones and expected engagement patterns
