Installation
============

This guide will help you install and configure Django Email Learning in your Django project.

Quick Start (Recommended)
--------------------------

The fastest way to get a working Django project with Django Email Learning is the interactive setup command:

.. code-block:: bash

    pip install django-email-learning
    django-email-learning-init

This command will:

- Create and activate a virtual environment (if you are not already in one)
- Ask for your project name and URL prefix
- Optionally enable AI text-editing features (OpenAI) and Google Workspace group enrollment
- Install Django and all required dependencies
- Scaffold a new Django project with ``django_email_learning`` pre-configured in settings and URLs
- Generate secrets for ``JWT_SECRET_KEY`` and ``ENCRYPTION_SECRET_KEY`` and save them in a ``.env`` file
- Run database migrations
- Offer to create a Django superuser

After ``django-email-learning-init`` completes, start the development server:

.. code-block:: bash

    python manage.py runserver

Then open ``http://localhost:8000/<your-prefix>/platform/`` in your browser.

.. note::
   The setup command configures ``EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`` by default.
   This means emails are printed to the terminal rather than sent. To send real emails in development, configure
   an SMTP backend or a service such as Mailpit. See `Email Backend Configuration`_ below for details.

For an existing Django project, follow the manual steps below.

Prerequisites
-------------

- Python 3.10 or higher
- Django 5.0 or higher
- A configured email backend (for sending course emails)

Manual Installation Steps
--------------------------

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


**JWT_SECRET_KEY**

A dedicated secret key used for signing and verifying JSON Web Tokens (JWTs). It should be a long, random string, independent of Django's ``SECRET_KEY`` and ``ENCRYPTION_SECRET_KEY``.

Using a separate key ensures that a JWT secret compromise does not affect other parts of your application.

Same as all other sensitive configurations, it's a good practice to load this from an environment variable or a secure vault.


.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
    }


Optional Settings
~~~~~~~~~~~~~~~~~

**FROM_EMAIL**

The default email address for outgoing course emails. If not specified, falls back to Django's ``DEFAULT_FROM_EMAIL`` setting.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'FROM_EMAIL': 'courses@yourdomain.com',
    }

**TERMS_OF_SERVICE_URL**

Optional link to your terms of service. When provided, this link is displayed in the public enrollment dialog so learners can review your terms before submitting their email address.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'TERMS_OF_SERVICE_URL': 'https://yourdomain.com/terms',
    }

**QUIZ_DEFAULTS**

Optional configuration for the initial default values shown in the quiz form when creating a new quiz.

All values are boolean.

- ``LIMITED_ATTEMPTS``: Sets the default state of the Limited Attempts switch. When enabled, learners only have 2 attempts to pass the quiz. When disabled, learners can retry as many times as needed.
- ``IS_BLOCKING``: Sets the default state of the Blocking Quiz switch. When enabled, learners must pass the quiz to continue receiving course content. When disabled, the quiz is treated as practice and does not gate course progress.
- ``HAS_DEADLINE``: Sets the default state of the quiz deadline switch. When enabled, new quizzes start with a deadline. When disabled, new quizzes default to having no deadline.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'QUIZ_DEFAULTS': {
            'LIMITED_ATTEMPTS': True,
            'IS_BLOCKING': True,
            'HAS_DEADLINE': True,
        },
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
        'JWT_SECRET_KEY': 'another-very-long-random-string',
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
        'JWT_SECRET_KEY': 'another-very-long-random-string',
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

**PRIVATE_FILE_STORAGE_LOCATION**

The filesystem path where privately uploaded files will be stored. Unlike media files served via Django's ``MEDIA_URL`` which are publicly accessible, files stored here are **not** served publicly. They are only accessible through an authenticated endpoint, ensuring that sensitive files (such as assignment submissions or certificates) are protected and only available to authorised users.

If not specified, a default location will be used.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'PRIVATE_FILE_STORAGE_LOCATION': '/path/to/private/storage/',
    }

.. note::
   Ensure the directory exists and that the Django process has read/write permissions for the specified path.
   Do **not** place this directory inside your web server's publicly served document root, as doing so would defeat the purpose of private storage.

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
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'AI': {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'TEXT_EDITING_MODEL': LanguageModel.GPT_4O_MINI.model_name,
        },
    }

See `AI Configuration <technical/ai-configuration.html>`_ for full details.

**GOOGLE_OAUTH**

Optional configuration for Google Workspace group enrollment.

- Configure this only if you want to allow bulk enrolment of learners from a Google Workspace directory.
- If you do not use Google Workspace features, you can omit ``GOOGLE_OAUTH`` entirely.
- Install Google dependencies with ``pip install 'django-email-learning[google]'``.
- Add ``'django_email_learning.oauth_integrations'`` to ``INSTALLED_APPS`` when using this feature.
- You need a GCP project with an **OAuth 2.0 Web Application** credential. Set the authorised redirect URI to ``<SITE_BASE_URL>/oauth/google/callback/``.

.. code-block:: python

    INSTALLED_APPS = [
        # ... your other apps
        'django_email_learning',
        'django_email_learning.oauth_integrations',
        # ... more apps
    ]

Available keys:

- ``CLIENT_ID``: OAuth 2.0 client ID from the GCP console.
- ``CLIENT_SECRET``: OAuth 2.0 client secret from the GCP console.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'GOOGLE_OAUTH': {
            'CLIENT_ID': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
            'CLIENT_SECRET': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
        },
    }

**AMP_ENABLED**

Optional flag to enable AMP email rendering for supported clients.

By default, AMP email support is disabled. Enable it only after your sending domain is registered as a dynamic email sender with Google:

`Register dynamic email with Google <https://developers.google.com/workspace/gmail/ampemail/register>`_

If AMP is enabled, you must also add trusted AMP mail client origins to Django's ``CSRF_TRUSTED_ORIGINS`` so AMP form submissions are accepted.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'AMP_ENABLED': True,
    }

    CSRF_TRUSTED_ORIGINS = [
        'https://mail.google.com',
        'https://playground.amp.dev', # ⚠️ Do not include this in production - it's only needed for testing with the AMP playground
        # Add any other trusted AMP mail client origins you use
    ]

.. note::
   Keep AMP disabled in environments where you have not completed sender registration and trusted-origin configuration.

**DELIVERY_WORKERS**

Optional integer controlling how many threads the ``deliver_contents`` job uses to process deliveries concurrently. Defaults to ``1``, which preserves the original sequential behaviour.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'DELIVERY_WORKERS': 4,  # process up to 4 emails concurrently
    }

.. note::
   Set ``DELIVERY_WORKERS`` to a value your SMTP provider can handle — most transactional email services impose per-second rate limits. A value between 2 and 10 is typical. Each worker uses its own database connection, so ensure your database connection pool is sized accordingly.


**NEWSLETTERS**

Optional configuration for the newsletter feature.

- ``FROM_EMAIL``: The sender address used for newsletter sendouts. Overrides the top-level ``FROM_EMAIL`` and Django's ``DEFAULT_FROM_EMAIL`` for newsletter emails specifically. Useful when newsletters are sent from a different address than course emails.
- ``MAX_SUBSCRIBER_PER_NEWSLETTER``: The maximum number of subscribers allowed per newsletter. Defaults to ``500``. Once a newsletter reaches this limit it is hidden from the public subscription form and new subscriptions via the API are rejected with a ``400`` error. Existing subscribers are never affected.

.. code-block:: python

    DJANGO_EMAIL_LEARNING = {
        'SITE_BASE_URL': 'https://yourdomain.com',
        'ENCRYPTION_SECRET_KEY': 'your-very-long-random-string',
        'JWT_SECRET_KEY': 'another-very-long-random-string',
        'NEWSLETTERS': {
            'FROM_EMAIL': 'newsletter@yourdomain.com',
            'MAX_SUBSCRIBER_PER_NEWSLETTER': 1000,
        },
    }

.. note::
   ``MAX_SUBSCRIBER_PER_NEWSLETTER`` is enforced at the view level on both ``OrganizationView`` and ``NewsletterSubscribeView``. You can override ``get_max_subscribers()`` on either view class to apply custom limits (e.g. per-organisation quotas).


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
