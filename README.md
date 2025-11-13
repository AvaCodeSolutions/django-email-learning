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

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.
