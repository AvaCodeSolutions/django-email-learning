# Django Email Learning

A Django package for creating email-based learning platforms with IMAP integration and React frontend components.

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0+-green.svg)](https://www.djangoproject.com/)


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


## Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) to learn about our development process, how to set up the development environment, and how to submit pull requests.

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.
