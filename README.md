# Django Email Learning

A Django package for creating email-based learning platforms with IMAP integration and React frontend components.

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)


## ⚠️ Early Development Notice

**This project is currently in early development and is not yet ready for production use.**


## Quick Start

### Installation

```bash
pip install django-email-learning
```

### Django Setup

1. Add to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... your apps
    'django_email_learning',
]
```

2. Include URLs in your project:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ... your URLs
    path('email-learning/', include('django_email_learning.urls', namespace='django_email_learning')),
]
```

3. Run migrations:

```bash
python manage.py migrate
```

## Development

### Building Frontend Assets

The package includes pre-built React frontend assets. If you need to rebuild them:

```bash
./build_frontend.sh
```

This script will:
1. Install frontend dependencies
2. Build the React application using Vite
3. Copy the built assets to `django_email_learning/static/`

### Running in Development Mode

For development with hot module replacement, you can:

1. Start the Django development server:
```bash
python manage.py runserver
```

2. In a separate terminal, start the Vite dev server:
```bash
cd frontend
npm install
npm run dev
```

Note: The templates are configured to use static built assets. For live development, you may want to temporarily use django-vite (available as a dev dependency).

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.
