<p align="center">
  <img src="https://raw.githubusercontent.com/AvaCodeSolutions/django-email-learning/master/assets/Django2@2x.png" alt="Django Email Learning Logo" width="300">
  <br><br>
  <a href="https://opensource.org/licenses/BSD-3-Clause"><img src="https://img.shields.io/badge/License-BSD%203--Clause-blue.svg"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg"></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/django-5.0+-green.svg"></a>
  <img src="https://github.com/AvaCodeSolutions/django-email-learning/actions/workflows/pr-check.yml/badge.svg">
</p>

# Django Email Learning

A Django package for creating email-based learning platforms with IMAP integration and React frontend components.

## Sponsorship

Support our open-source work and community projects by sponsoring us through [GitHub Sponsors](https://github.com/sponsors/AvaCodeSolutions). Depending on your sponsorship tier, we can feature your logo and link on the project’s README and documentation.

[![Sponsor us](https://img.shields.io/badge/Sponsor_our_project-white?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/AvaCodeSolutions)

## What is django-email-learning?

**django-email-learning** is an open-source Django app, designed to provide a complete email-based learning platform.
It is inspired by the Darsnameh email-learning service, which unfortunately shut down in July 2017. This library aims to revive that concept and make it accessible to anyone who wants to launch a similar service.

If you find this project useful, a ⭐ on GitHub helps others discover it.

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

### Quick Start

The fastest way to get a working development environment is the interactive setup command:

```bash
pip install django-email-learning
django-email-learning-init
```

This sets up a new Django project with `django_email_learning` pre-configured — virtual environment, secrets, migrations, and a superuser — in one go. See the [Installation Guide](https://django-email-learning.readthedocs.io/en/latest/installation.html) for the full walkthrough.

### Manual Installation

For existing Django projects, follow these steps.

#### 1. Install the Package

```bash
pip install django-email-learning
```

#### 2. Add to INSTALLED_APPS

Add `django_email_learning` to your `INSTALLED_APPS` in the Django settings file:

```python
INSTALLED_APPS = [
    ...
    'django_email_learning',
]
```

#### 3. Configure Settings

Add the required configuration for the site base URL in your Django settings:

```python
DJANGO_EMAIL_LEARNING = {
    "SITE_BASE_URL": "<YOUR_SITE_BASE_URL_STARTING_WITH_HTTP>",
    "ENCRYPTION_SECRET_KEY": "<LONG_RANDOM_STRING>",
    "JWT_SECRET_KEY": "<LONG_RANDOM_STRING>",
}
```

`ENCRYPTION_SECRET_KEY` should be a long random string used to protect sensitive values such as stored API Keys.

#### 4. Configure Media Files

This app uses Django's MEDIA files to save organization logos. Ensure your media settings are configured correctly. See the [MEDIA_URL setting](https://docs.djangoproject.com/en/6.0/ref/settings/#media-url) for details.

#### 5. Run Migrations

```bash
python manage.py migrate
```

#### 6. Add URLs

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

#### Access Control Notes

- **Platform Access:** You need to be logged in to access the `/platform` sub-URL, which is used for managing courses and viewing learner progress.


## Usage

### Newsletters

django-email-learning includes a built-in newsletter system. Platform admins can create newsletters per organisation, grow a subscriber list, and schedule email campaigns (sendouts) that are delivered automatically.

#### Quick start

1. Create a newsletter from the platform UI under an organisation.
2. Share the public subscription form (available on the organisation's public page) so users can subscribe.
3. Schedule a sendout with a subject, rich-text body, and an optional send date.
4. Run the delivery command (or trigger it via the API) to send emails to all active subscribers:

```bash
python manage.py send_newsletters
```

You can also trigger delivery via HTTP:

```http
GET /your_preferred_path/api/jobs/send_newsletters/
Authorization: Bearer <API_KEY>
```

#### Configuration

All newsletter settings live under the `DJANGO_EMAIL_LEARNING` dictionary:

| Key | Default | Description |
|-----|---------|-------------|
| `NEWSLETTERS.FROM_EMAIL` | `FROM_EMAIL` → `webmaster@localhost` | Sender address for newsletter emails |
| `NEWSLETTERS.MAX_RETRIES` | `3` | Per-subscriber delivery retry limit before a delivery is permanently failed |
| `NEWSLETTERS.MAX_SUBSCRIBERS` | unlimited | Maximum subscribers allowed per newsletter (can be overridden per-view by subclassing and overriding `get_max_subscribers()`) |
| `SENDOUT_QUEUE` | `DatabaseSendoutQueue` | Import path to a custom queue class (must implement `TaskQueueProtocol[SendoutDelivery]`) |
| `SITE_BASE_URL` | `""` | Base URL prepended to the unsubscribe link in every email |

#### Optional: auto-subscribe on course enrollment

Link a newsletter to a course in the platform UI (or via API). When a learner enrolls in that course they are automatically subscribed to the linked newsletter.

### Content Delivery

This app uses the email backend defined in Django settings to deliver course content. Assuming you have active courses and enrollments, you need to schedule a job that runs the content delivery management command periodically (e.g., using cron or a cloud scheduler).

Execute the content delivery job using:

```bash
python manage.py deliver_contents
```

You can also trigger this job via API, which is useful when running from an external scheduler (for example, cloud scheduler services):

```http
GET /your_preferred_path/api/jobs/deliver_contents/
Authorization: Bearer <API_KEY>
```

This endpoint requires an API key. You can generate and manage API keys from Platform Settings > API Keys in the platform UI.

## Contributing

We welcome contributions! Please read our [Contributing Guide](https://github.com/AvaCodeSolutions/django-email-learning/blob/master/CONTRIBUTING.md) to learn about our development process, how to set up the development environment, and how to submit pull requests.

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](https://github.com/AvaCodeSolutions/django-email-learning/blob/master/LICENSE) file for details.
