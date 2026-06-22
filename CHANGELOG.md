# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [1.0.0] — 2026-06-22

First stable release. The public API, data models, and migration history are
now considered stable. Future releases will follow semantic versioning.

### Highlights

- Complete course authoring platform with lesson, quiz, and assignment content types
- Learner enrollment lifecycle (enroll → verify → deliver → graduate → certificate)
- Role-based access control (admin, editor, instructor, viewer)
- IMAP integration for email-based learner interactions
- Google Workspace bulk enrollment (optional)
- AI-assisted lesson editing (optional)
- Platform feature flags via `PlatformFeature` enum with override support
- Configurable quiz defaults (blocking, deadline, limited attempts, reminder interval)
- Certificate email on course completion (per-course opt-in via `send_certificate`)
- REST API for all platform and learner-facing operations
- Squashed migration history — new installs use a single `0001_initial` migration

### Upgrade note for beta installs

If you are upgrading from a beta version that already has an applied migration
history, fake the squashed migration rather than running it:

```bash
python manage.py migrate --fake django_email_learning 0001_initial
```
