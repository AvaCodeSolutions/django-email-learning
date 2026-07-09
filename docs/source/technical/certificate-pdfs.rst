Certificate PDFs
=================

When a course has ``send_certificate`` enabled, a learner who submits the "enter your name" form after completing it is issued a ``Certificate``. In addition to the existing in-browser certificate page, a PDF version of that certificate is generated and emailed to the learner, and the same PDF is available for on-demand download.

Installation
------------

PDF generation uses `WeasyPrint <https://doc.courtbouillon.org/weasyprint/stable/>`_, which is an optional dependency so that projects not using certificates don't need to install it:

.. code-block:: bash

    pip install django-email-learning[certificates]

WeasyPrint depends on system libraries (Pango, Cairo, HarfBuzz, GDK-Pixbuf) that aren't installed by pip. See the `WeasyPrint installation guide <https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation>`_ for your platform.

Emailing the PDF
-----------------

Sending is deferred to a background job (``send_certificate_pdfs``, see :doc:`management-commands`) rather than happening synchronously when the certificate is issued, so it doesn't block the request and can retry on failure.

Configuration is nested under ``DJANGO_EMAIL_LEARNING``:

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        "CERTIFICATES": {
            "MAX_RETRIES": 3,  # default: 3
        },
        ...
    }

The job must be run on a schedule, the same way as ``send_newsletters`` or ``deliver_contents`` (every few minutes is reasonable).

Replacing the queue
~~~~~~~~~~~~~~~~~~~~

By default, pending certificates are claimed from the database via :class:`DatabaseCertificatePdfQueue <django_email_learning.services.defaults.database_certificate_pdf_queue.DatabaseCertificatePdfQueue>`. If you want to back delivery with something else (e.g. a Pub/Sub topic or SQS queue) instead of polling the database, implement :class:`TaskQueueProtocol <django_email_learning.ports.task_queue_protocol.TaskQueueProtocol>` for ``Certificate`` and point the ``CERTIFICATE_PDF_QUEUE`` setting at its dotted import path:

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        "CERTIFICATE_PDF_QUEUE": "myapp.queues.PubSubCertificatePdfQueue",
        ...
    }

This mirrors ``SENDOUT_QUEUE`` for newsletter delivery.

Existing certificates on upgrade
---------------------------------

Certificates issued before this feature was installed predate PDF-email delivery. The migration that adds this feature marks all pre-existing certificates as already handled, so upgrading does **not** retroactively email a PDF for every certificate ever issued — only certificates issued after the upgrade are queued for a PDF email.

Downloading the PDF on demand
-------------------------------

The same PDF (regenerated fresh each time, not cached) is available for download without waiting for the background job:

.. code-block:: text

    GET /your_preferred_path/personalised/certificate/<certificate_number>/download/

This reuses the same generation function as the email job, so there's a single source of truth for what a certificate PDF looks like.
