Installation
============

This guide will help you install and configure Django Email Learning in your Django project.

.. warning::
   The library is currently in its early stages of development. The current version is an alpha release,
   and while it includes core features, it may not yet be suitable for production use and future updates may introduce breaking changes.


Prerequisites
-------------

- Python 3.10 or higher
- Django 5.0 or higher
- A configured email backend (for sending course emails)

Installation Steps
------------------

1. **Install the Package**

   Install Django Email Learning via pip:

   .. code-block:: bash

       pip install django-email-learning

2. **Add to INSTALLED_APPS**

   Add 'django_email_learning' to your INSTALLED_APPS in settings.py:

   .. code-block:: python

       INSTALLED_APPS = [
           # ... your other apps
           'django_email_learning',
           # ... more apps
       ]

3. **Run Database Migrations**

   Create the necessary database tables:

   .. code-block:: bash

       python manage.py migrate django_email_learning

4. **Configure URLs**

   Add Django Email Learning URLs to your project's main urls.py:

   .. code-block:: python

       from django.urls import path, include

       urlpatterns = [
           # ... your other URL patterns
           path('email-learning/', include('django_email_learning.urls')),
           # ... more URL patterns
       ]

   You can change ``email-learning/`` to any URL path you prefer. This will make:

   - **Platform (Admin Interface)**: Available at ``/email-learning/platform/``
   - **Public Course Pages**: Available at ``/email-learning/public/organization/<org_id>/``
   - **API Endpoints**: Available under ``/email-learning/api/``

Access Control
--------------

**Platform Access**

The course management platform (``/platform/``) requires authentication and is accessible to:

- Django superusers
- Users assigned as Organization users (managed via Django admin panel)

.. note::
   Since the platform views require authentication, ensure your Django project has authentication views configured.
   You can use Django's built-in authentication views by including them in your URLconf.
   See `Django's authentication views documentation <https://docs.djangoproject.com/en/6.0/topics/auth/default/#module-django.contrib.auth.views>`_ for setup instructions.

**Public Access**

Public course enrollment pages are accessible without authentication and are designed for learners to discover and enroll in courses.

Configuration
-------------

Django Email Learning requires specific configuration in your Django settings. Add a ``DJANGO_EMAIL_LEARNING`` dictionary to your ``settings.py``:

Required Settings
~~~~~~~~~~~~~~~~~

**SITE_BASE_URL**

The base URL of your site, used to generate absolute URLs in emails and course links.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
    }

Optional Settings
~~~~~~~~~~~~~~~~~

**FROM_EMAIL**

The default email address for outgoing course emails. If not specified, falls back to Django's ``DEFAULT_FROM_EMAIL`` setting.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'FROM_EMAIL': 'courses@yourdomain.com',
    }

Email Backend Configuration
---------------------------

Django Email Learning sends course content and notifications via email. Ensure your Django project has a properly configured email backend:

.. code-block:: python

    # Example SMTP configuration
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'your-email@gmail.com'
    EMAIL_HOST_PASSWORD = 'your-app-password'
    DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

Management Command Scheduling
-----------------------------
To automate content delivery, schedule the ``deliver_contents`` management command to run at regular intervals (e.g., every 15-60 minutes) using a task scheduler like cron or Celery Beat.

See `Management Commands <technical/management-commands.html>`_ for more details.
