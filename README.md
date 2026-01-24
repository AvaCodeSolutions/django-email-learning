<p align="center">
  <img src="https://raw.githubusercontent.com/AvaCodeSolutions/django-email-learning/master/assets/Django2@2x.png" alt="Django Email Learning Logo" width="300">
</p>

# Django Email Learning

A Django package for creating email-based learning platforms with IMAP integration and React frontend components.

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)
![Tests](https://github.com/AvaCodeSolutions/django-email-learning/actions/workflows/pr-check.yml/badge.svg)


## ⚠️ Early Development Notice

**This project is currently in early development and is not yet ready for production use.**

## What is django-email-learning?

**django-email-learning** is an open-source Django app, currently under active development, designed to provide a complete email-based learning platform.
It is inspired by the Darsnameh email-learning service, which unfortunately shut down in July 2017. This library aims to revive that concept and make it accessible to anyone who wants to launch a similar service.

### Why an email learning platform?

An email learning platform is a type of e-learning system where course content is delivered directly to learners’ inboxes. Platform admins can create courses, lessons, and quizzes, and configure the timing rules that determine when each next lesson or quiz is sent.

The system exposes management commands and/or API endpoints that can be triggered by cron jobs or cloud schedulers to:

- Track learner progress

- Send lessons and quizzes via email

- Handle automated transitions between course steps

Additionally, the platform can issue online completion certificates that learners can verify using a QR code.

### Why use email for e-learning?

While modern e-learning platforms often rely heavily on video content and complex web interfaces, email remains a powerful and inclusive channel. Some of the reasons:

- **Low bandwidth requirement:** Email works well in regions with slow or unstable internet.

- **High accessibility:** No need to install apps or log into a portal—lessons arrive directly in the inbox.

- **Resilience to censorship:** Emails are often less likely to be blocked than certain websites or platforms under restrictive governments.

- **Simplicity:** Email is universal, familiar, and works on virtually any device.

## Documentation

Comprehensive documentation is available at [django-email-learning.readthedocs.io](https://django-email-learning.readthedocs.io), including:

- **Installation Guide**: Step-by-step setup instructions
- **Platform Management**: Creating organizations, courses, and managing learners
- **Technical Reference**: Management commands and configuration
- **Usage Examples**: Real-world implementation scenarios

## Installation

This is a Django app, so we assume you already have Django installed.

### 1. Install the Package

```bash
pip install django-email-learning
```

### 2. Add to INSTALLED_APPS

Add `django_email_learning` to your `INSTALLED_APPS` in the Django settings file:

```python
INSTALLED_APPS = [
    ...
    'django_email_learning',
]
```

### 3. Configure Settings

Add the required configuration for the site base URL in your Django settings:

```python
DJANGO_EMAIL_LEARNING = {
    "SITE_BASE_URL": "<YOUR_SITE_BASE_URL_STARTING_WITH_HTTP>"
}
```

### 4. Configure Media Files

This app uses Django's MEDIA files to save organization logos. Ensure your media settings are configured correctly. See the [MEDIA_URL setting](https://docs.djangoproject.com/en/6.0/ref/settings/#media-url) for details.

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Add URLs

Include the app URLs in your main Django URLs configuration:

```python
from django.urls import path, include
from django_email_learning import urls as email_learning_urls

urlpatterns = [
    ...
    path('your_preferred_path/', include(email_learning_urls, namespace='django_email_learning')),
]
```

The platform will be accessible at `your_preferred_path/platform/`.

### Access Control Notes

- **Platform Access:** You need to be logged in to access the `/platform` sub-URL, which is used for managing courses and viewing learner progress.

- **Current MVP Limitations:** In the current MVP version, you can use the superuser account. Other staff users can access the platform only if they are programmatically assigned to an organization. The UI to assign members with different roles to organizations is not yet implemented, however, the access control for those roles is in place.

## Usage

### Content Delivery

This app uses the email backend defined in Django settings to deliver course content. Assuming you have active courses and enrollments, you need to schedule a job that runs the content delivery management command periodically (e.g., using cron or a cloud scheduler).

Execute the content delivery job using:

```bash
python manage.py deliver_contents
```

## Contributing

We welcome contributions! Please read our [Contributing Guide](https://github.com/AvaCodeSolutions/django-email-learning/blob/master/CONTRIBUTING.md) to learn about our development process, how to set up the development environment, and how to submit pull requests.

## Sponsorship

Support our open-source work and community projects by sponsoring us through [GitHub Sponsors](https://github.com/sponsors/AvaCodeSolutions) or [Open Collective](https://opencollective.com/django-email-learning). Depending on your sponsorship tier, we can feature your logo and link on the project’s README and documentation.

[![Sponsor us](https://img.shields.io/badge/Sponsor_our_project-white?style=for-the-badge&logo=githubsponsors)](https://opencollective.com/django-email-learning)


## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](https://github.com/AvaCodeSolutions/django-email-learning/blob/master/LICENSE) file for details.
