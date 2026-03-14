AI Configuration
================

Django Email Learning supports optional AI-powered text editing features.

If you do not use AI editing tools, you can omit the ``AI`` section entirely.

Prerequisites
-------------

Before configuring AI settings, install the AI optional dependencies:

.. code-block:: bash

    pip install 'django-email-learning[ai]'

Then include the AI app in ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        # ... your other apps
        'django_email_learning',
        'django_email_learning.ai',
        # ... more apps
    ]

Settings
--------

Configure AI under ``DJANGO_EMAIL_LEARNING['AI']`` in your Django ``settings.py``.

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

``OPENAI_API_KEY``
~~~~~~~~~~~~~~~~~~

API key used for OpenAI requests.

- Required only when you want to use AI editing features.
- Keep this value in environment variables or a secure secret manager.

``TEXT_EDITING_MODEL``
~~~~~~~~~~~~~~~~~~~~~~

Model name used by AI text editing features.

- Value should match one of the names exposed by ``LanguageModel``.
- Defaults can be set in your own project settings.

Available Models
----------------

The package currently provides OpenAI-backed models:

- ``gpt-4o-mini``
- ``gpt-5-nano``
- ``gpt-5-mini``
