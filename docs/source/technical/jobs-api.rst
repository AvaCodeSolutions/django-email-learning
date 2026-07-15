Jobs HTTP API
=============

Every job listed in :doc:`management-commands` (except ``rotate_encryption_key``) has an HTTP trigger endpoint under ``/api/jobs/...``, authenticated via :doc:`../platform/api_keys`, so it can be run from an external scheduler or CI/CD pipeline instead of (or alongside) server-side cron.

HTTP Trigger Endpoints Run Asynchronously
------------------------------------------

.. versionchanged:: 2.0.0

   Every job's HTTP trigger endpoint (``/api/jobs/...``) now hands the job off to a pluggable executor instead of running it inline and blocking the request. The response comes back as soon as the job starts:

   - ``202`` with a ``job_execution_id`` — the job was accepted and is running.
   - ``409`` with the ``job_execution_id`` of the already-running execution — another instance of that job is still in progress (jobs are mutually exclusive per ``job_name``).
   - ``500`` — the job could not even be handed off to the executor (e.g. the configured executor backend is unreachable).

   Success or failure of the job itself is no longer reflected in the trigger response — poll ``GET /api/jobs/executions/<job_execution_id>/`` (see `Checking Job Execution Status`_ below) to find out how it finished.

   By default, jobs run on an in-process ``ThreadPoolExecutor``. To use Celery, RQ, Django-Q, or another backend instead, implement :class:`JobExecutorProtocol <django_email_learning.ports.job_executor_protocol.JobExecutorProtocol>` and point the ``JOB_EXECUTOR`` setting at it — see :doc:`../installation` for configuration details.

Checking Job Execution Status
------------------------------

.. code-block:: http

    GET /your_preferred_path/api/jobs/executions/<job_execution_id>/
    Authorization: Bearer <API_KEY>

Returns:

.. code-block:: json

    {
        "job_execution_id": 42,
        "job_name": "deliver_contents",
        "status": "completed",
        "started_at": "2026-07-15T04:00:00Z",
        "finished_at": "2026-07-15T04:00:03Z",
        "error": null
    }

``status`` is one of ``running``, ``completed``, ``failed``, or ``stale`` (a run that never reached ``completed``/``failed`` within the staleness window). ``error`` is populated with the exception message when ``status`` is ``failed``.
