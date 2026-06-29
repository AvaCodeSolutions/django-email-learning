# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [1.2.0] — 2026-06-29

### Added

- **`CourseView.can_create_course()` hook** — library users can now subclass `CourseView` and override `can_create_course(request, organization_id) -> bool` to inject custom course creation logic (e.g. plan-based limits, feature flags, subscription checks). The default implementation returns `True`, so existing behaviour is unchanged. Returning `False` rejects the request with a `403` before any database work happens.

---

## [1.1.1] — 2026-06-27

### Fixed

- `send_newsletters`: when every subscriber delivery permanently fails, `scheduled_at` is now bumped 10 minutes into the future after resetting deliveries. Previously the sendout's past `scheduled_at` caused the next job run to pick it up immediately, creating a tight retry loop against a broken email configuration.

---

## [1.1.0] — 2026-06-26

Newsletter feature: organisations can now manage newsletters, grow a subscriber list, and send scheduled email campaigns directly from the platform.

### Added

- **Newsletter management** — create and manage newsletters per organisation with title and language; link a newsletter to a course so learners auto-subscribe on enrollment
- **Subscriber management** — public subscription form on the organisation page; per-subscriber unsubscribe token and one-click unsubscribe link in every email; configurable max-subscriber cap (`DJANGO_EMAIL_LEARNING["NEWSLETTERS"]["MAX_SUBSCRIBERS"]`); subscriber list with CSV export in the org admin UI
- **Sendout scheduling** — create and schedule sendouts with subject, rich-text body, and inline image uploads; edit or delete a sendout before it is sent
- **Automated email delivery** — `send_newsletters` management command and matching HTTP trigger endpoint (`/api/jobs/send_newsletters/`); per-subscriber `SendoutDelivery` tracking with configurable retry limit (`NEWSLETTERS.MAX_RETRIES`, default 3); best-effort completion (marked SENT when ≥1 subscriber received it); automatic reset and dual-channel alert (log + metric) when every delivery fails, indicating a configuration-level issue
- **HTML email template** — `emails/newsletter_sendout.html` is attached as an alternative part; plain-text fallback included; descriptive unsubscribe sentence rendered from the template
- **New settings keys** under `DJANGO_EMAIL_LEARNING`:
  - `NEWSLETTERS.FROM_EMAIL` — sender address for newsletter emails (falls back to `FROM_EMAIL`, then `webmaster@localhost`)
  - `NEWSLETTERS.MAX_RETRIES` — per-subscriber delivery retry limit (default `3`)
  - `NEWSLETTERS.MAX_SUBSCRIBERS` — subscriber cap per newsletter (default unlimited)
  - `SENDOUT_QUEUE` — optional custom queue class (defaults to `DatabaseSendoutQueue`)
- **New metric** — `sendout_all_deliveries_failed` emitted when every subscriber delivery permanently fails for a sendout

### Migration note

This release ships a single squashed migration (`0002_newsletter_feature`) that covers the entire newsletter feature. New installs will apply it automatically.

If you are upgrading from a pre-release build that already has `0002`–`0005` applied, fake the squashed migration instead of running it:

```bash
python manage.py migrate --fake django_email_learning 0002_newsletter_feature
```

---

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
