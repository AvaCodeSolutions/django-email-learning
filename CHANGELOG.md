# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [1.7.0] — 2026-07-03

### Added

- **Enable/disable error feedback and inline "enable it" action** — `EnableCourseSwitchPopup` now shows the API's error message (e.g. the "no content" guard from 1.5.0) as an alert inside the confirmation dialog instead of failing silently, and disables its buttons while the request is in flight. The single-course page's disabled-course banner now renders "enable it" as a clickable link that opens the same confirmation dialog; on success the banner, enrollment analytics summary, and enroll button all update immediately without a page reload.
- **`window.DialogAPI` available on every platform page** — moved from the single-course page to the shared navbar layer (`Base.jsx`), so `window.DialogAPI` (`show`, `close`, `setMaxWidth`, `setCloseOnBackdropClick`, `getDialogBackdropClickSetting`) is available consistently across the whole platform instead of disappearing as soon as the user navigates away from a course. The course page keeps its own separate local dialog for its internal forms, unaffected.

---

## [1.6.0] — 2026-07-03

### Added

- **Script/style URL support for navbar custom components** — each entry in `appContext.navbarCustomComponents` can now include `styleUrl`/`scriptUrl` in addition to `html`, matching the `WebComponent` shape already used for the course-page and sidebar custom components. `BasePlatformView` collects the unique `styleUrl`/`scriptUrl` values across all navbar slots and injects one `<link>`/plain `<script src="...">` tag per unique URL (deduplicated across slots, no `type="module"`).

---

## [1.5.0] — 2026-07-03

### Added

- **Disabled-course guards on the course page and API** — the single-course page now exposes `appContext.courseEnabled` and shows a warning banner while hiding the enrollment analytics summary when a course is disabled. The "Enroll Learner" button (manual email and Google Workspace group enrollment) is disabled while the course is disabled. Server-side, enabling a course (`enabled: true`) with no `CourseContent` now fails with a clear `409` error instead of silently succeeding.

---

## [1.4.0] — 2026-07-02

### Added

- **`navbarCustomComponents` slot for the desktop navbar** — `appContext.navbarCustomComponents` (default `[]`) lets views fill the previously empty space in the desktop navbar with one or more independent widgets. Views populate it directly in `get_context_data` (the same pattern `CustomComponentCourseView` already uses for `customComponent`) with a list of `{slot, html}` entries, each rendered via `dangerouslySetInnerHTML` in `MenuBar.jsx`, keyed by slot, and shown only at `md`+ widths.

---

## [1.3.0] — 2026-07-01

### Added

- **`NewsletterAccessMixin` for newsletter API views** — library users can now override `newsletter_access_allowed(request, *args, **kwargs) -> bool` (default `True`) to gate access to the newsletter feature (e.g. behind a plan or feature flag), independent of the existing role-based `accessible_for` checks. Applied to all newsletter API views (`NewsletterView`, `SingleNewsletterView`, `SendoutView`, `SingleSendoutView`, `SubscriberView`, `SingleSubscriberView`, `SubscribersCsvExportView`).
- **`EditTextView` access hook and `instructor` role** — `EditTextView` now supports an overridable `ai_edit_text_access_allowed(request, *args, **kwargs) -> bool` hook (default `True`), checked before the role-based access check. The `instructor` role has also been added to the allowed roles for AI text editing, matching the pattern already used for content-editing actions elsewhere (courses, learners, oauth).
- **`BaseOAuthSessionHandler` and overridable OAuth request serializer** — `BaseGroupEnrollmentHandler` now extends a new shared `BaseOAuthSessionHandler`, so future non-enrollment OAuth handlers (e.g. authentication-only) won't inherit enrollment-specific fields like `course_id`. The shared base adds an `access_allowed(request) -> bool` hook (default `True`), checked in `SessionsView` before the role-based check. A new `OAuthSessionRequestMixin` with `get_create_session_request_class()` lets library users plug in a custom `CreateSessionRequest` to support their own handler types, kept in sync between `SessionsView` and `RedirectView`.

---

## [1.2.4] — 2026-06-30

### Changed

- **Split `platform/api/views.py` into domain modules** — the 600+ line flat file has been replaced with a `platform/api/views/` package grouping views by domain (`courses`, `learners`, `organisations`, `newsletters`, `oauth`, `assignments`, `misc`). All existing imports and URL configs are unchanged.
- **Split `platform/views.py` into domain modules** — same treatment for the platform-facing views, now organised under `platform/views/` (`base`, `courses`, `learners`, `organisations`, `newsletters`, `misc`).
- **Split `platform/api/serializers.py` into domain modules** — the 1462-line flat serializers file is now a `platform/api/serializers/` package with one module per domain plus a `common.py` for shared types that prevents circular imports. All 60+ classes remain importable from the same path.
- **Ruff configuration** — added `[tool.ruff]` config to `pyproject.toml` with `target-version = "py312"`, isort rule set (`I`), and `known-first-party` for consistent import ordering across the codebase.
- **ESLint updated to v10.6.0.**

---

## [1.2.3] — 2026-06-29

### Fixed

- **`ImageUpload` component uploaded to wrong organisation** — the component hardcoded `/organizations/1/files/` in its upload URL, causing image uploads to always target org 1 regardless of the active organisation. An `organizationId` prop has been added and all four call sites (`OrganizationForm`, `UserForm`, `CourseForm`, `CreateInstructorForm`) now pass the correct org ID.

---

## [1.2.2] — 2026-06-29

### Fixed

- **Org admin can now edit their organisation** — users with the `org_admin` role were incorrectly blocked from editing their organisation's name, description, logo, and other fields. The API was guarded by `is_platform_admin()` instead of the role-scoped `accessible_for` check, and the frontend edit button was hidden behind `isPlatformAdmin`. Both are now fixed: org admins can edit their own organisation but not others, and platform admins retain full access including delete.

---

## [1.2.1] — 2026-06-29

### Added

- **`can_create_course` in create and delete responses** — the `POST /courses/` (create) and `DELETE /courses/{id}/` (delete) API responses now include a `can_create_course: bool` field, evaluated after the operation completes. This allows the frontend to update its UI immediately after a mutation without an extra round-trip.
- **Frontend reacts to `can_create_course`** — the *Add Course* button is now disabled (rather than hidden) when `can_create_course` is `false`, and re-enables automatically after a course is deleted if the hook permits it.
- **Customisable blocked-state message** — library users can set `cannotCreateCourseMessage` in the app context to a plain string or HTML (including links) which is displayed as an info alert below the disabled button. Useful for directing users to an upgrade page when a plan limit is reached.

---

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
