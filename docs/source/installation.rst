Installation
============

This guide will help you install and configure Django Email Learning in your Django project.

.. important::
   The library is currently in its early stages of development. The current version is an beta release,
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

   If you want to use AI editing tools, install with the AI optional extra:

   .. code-block:: bash

       pip install 'django-email-learning[ai]'

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


**ENCRYPTION_SECRET_KEY**

A secret key used for encrypting sensitive data. It should be a long, random string.
This will be used for encrypting API keys and IMAP passwords. This key will be used for bidirectional encryption/decryption, so keep it secure.

Same as all other sensitive configurations, it's a good practice to load this from an environment variable or a secure vault.

.. important::
   Changing this key after data has been created will prevent access to previously encrypted data. Chaning requires re-encrypting all existing data with the new key.


.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
    }


Optional Settings
~~~~~~~~~~~~~~~~~

**FROM_EMAIL**

The default email address for outgoing course emails. If not specified, falls back to Django's ``DEFAULT_FROM_EMAIL`` setting.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'FROM_EMAIL': 'courses@yourdomain.com',
    }

**SIDEBAR.CUSTOM_COMPONENT**

Optional configuration for injecting a custom component in the platform sidebar.

- ``SCRIPT_URL``: URL of the JavaScript module that registers your custom element.
- ``STYLE_URL``: Optional stylesheet URL for the component (use ``None`` if not needed).
- ``COMPONENT_TAG``: HTML tag rendered in the sidebar.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'SIDEBAR': {
            'CUSTOM_COMPONENT': {
                'SCRIPT_URL': 'url/path-to-your-component.js',
                'STYLE_URL': 'url/path-to-your-component.css',
                'COMPONENT_TAG': '<your-component />',
            }
        },
    }

**LOGO**

Optional configuration for branding assets in the platform header.

- ``HORIZONTAL_LOCKUP``: Used on mobile devices where the sidebar is not open by default and the logo is shown in the top navbar.
- ``VERTICAL_LOCKUP``: Used for sidebar-oriented layouts.

    - ``LIGHT_BACKGROUND``: Logo URL/path for light backgrounds.
    - ``DARK_BACKGROUND``: Logo URL/path for dark backgrounds.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'LOGO': {
            'HORIZONTAL_LOCKUP': {
                'LIGHT_BACKGROUND': 'url/path-to-horizontal-logo-for-light-background.png',
                'DARK_BACKGROUND': 'url/path-to-horizontal-logo-for-dark-background.png',
            },
            'VERTICAL_LOCKUP': {
                'LIGHT_BACKGROUND': 'url/path-to-vertical-logo-for-light-background.png',
                'DARK_BACKGROUND': 'url/path-to-vertical-logo-for-dark-background.png',
            },
        },
    }

**AI**

Optional configuration for AI-powered text editing features.

- Configure this only if you have an OpenAI account and want to use AI edit tools.
- If you do not use AI features, you can omit ``AI`` entirely.
- Install AI dependencies with ``pip install 'django-email-learning[ai]'``.
- Add ``'django_email_learning.ai'`` to ``INSTALLED_APPS`` when using AI tools.

.. code-block:: python

    INSTALLED_APPS = [
        # ... your other apps
        'django_email_learning',
        'django_email_learning.ai',
        # ... more apps
    ]

Available keys:

- ``OPENAI_API_KEY``: OpenAI API key used for AI requests.
- ``TEXT_EDITING_MODEL``: OpenAI model name used by text editing.

Currently supported built-in models are:

- ``gpt-4o-mini``
- ``gpt-5-nano``
- ``gpt-5-mini``

.. code-block:: python

    from django_email_learning.ai.language_models import LanguageModel

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'AI': {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'TEXT_EDITING_MODEL': LanguageModel.GPT_4O_MINI.model_name,
        },
    }

See `AI Configuration <technical/ai-configuration.html>`_ for full details.

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
