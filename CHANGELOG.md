# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [1.16.0] — 2026-07-12

### Added

- **Configurable `SENDOUT_ALLOWED_RESOLVER` for newsletter sendouts** — `DJANGO_EMAIL_LEARNING["NEWSLETTERS"]["SENDOUT_ALLOWED_RESOLVER"]` is a dotted-path callable `(sendout: Sendout) -> bool`, checked once per due sendout in `DatabaseSendoutQueue` right before it's fanned out to subscribers. Defaults to always-allowed. Mirrors the existing `LEARNERS_CAP_RESOLVER` pattern, and is useful for e.g. capping how many sendouts an organization can send per period. A denied sendout is moved straight to a new terminal `Sendout.Status.BLOCKED` state (`blocked_reason="denied_by_resolver"`) rather than retried, since a cap that's already hit this poll will almost certainly still be hit moments later.
- **`SENDOUT_BLOCKED_MESSAGE` setting** — an optional plain string shown as a tooltip next to a sendout's "Blocked" status in the platform UI, so library users can explain to admins why sendouts get blocked, instead of a generic fallback message.

---

## [1.15.0] — 2026-07-11

### Added

- **Organization logo on verify-enrollment/unsubscribe/OAuth result pages** — these pages now resolve the relevant organization (via the enrollment, the unsubscribe token, or the course tied to the OAuth session) and show its uploaded logo, falling back to the platform-wide `DJANGO_EMAIL_LEARNING["LOGO"]` setting (or the built-in default) when the organization has none.
- **"You can now close this window" hint** — shown under the success/error message on the verify-enrollment/unsubscribe/OAuth result pages once there's nothing left for the user to do.

### Changed

- **Redesigned verify-enrollment/unsubscribe/OAuth result page layout** — the card now fills the viewport height instead of hugging the top with a lot of empty space below on desktop, content is positioned using a golden-ratio split rather than dead-centering, and the drop shadow is softer.

---

## [1.14.1] — 2026-07-10

### Fixed

- **Learners cap counted every learner, not just active ones** — `Organization.can_enroll_learner()` counted every `Learner` row against `MAX_LEARNERS_PER_ORGANIZATION`, regardless of enrollment status, so a learner with no enrollment (or only an unverified/completed/deactivated one) still counted toward the cap. It now counts only distinct learners with at least one active enrollment.

---

## [1.14.0] — 2026-07-10

### Fixed

- **Learner photos stored in private storage, not public** — `Learner.photo` (including photos imported during Google Workspace group enrollment) was previously saved via Django's default public media storage, so anyone with the URL could view a learner's photo without authentication. It now uses the existing private-storage mechanism (`PRIVATE_FILE_STORAGE_ALIAS`/`PRIVATE_FILE_STORAGE_LOCATION`, or a local `private_files/` folder if unconfigured), served through an access-controlled endpoint. `PrivateFileView`'s allowed roles were broadened from admin/instructor to admin/editor/instructor/viewer to match who can already see the Learners page. Existing photos already in public storage are left as-is and continue to work via a fallback; only new photos go to private storage going forward.
- **Google Workspace group enrollment OAuth redirect failing with "Scope has changed"** — Google commonly grants additional scopes (`openid`, `userinfo.email`, `userinfo.profile`) beyond what's requested, especially once a user has previously authorized the same OAuth client for another purpose. `oauthlib` treated any such scope mismatch as fatal, turning an otherwise-successful authorization into a 400. `OAUTHLIB_RELAX_TOKEN_SCOPE` is now set before the token exchange so a superset of granted scopes is no longer rejected.

---

## [1.13.3] — 2026-07-09

### Changed

- **Minor style improvement** — x-padding removed from the navbar custom component for the mobile view so it can be adjusted by component creators.

---

## [1.13.2] — 2026-07-09

### Fixed

- **`navbarCustomComponents` hidden on mobile** — these were only rendered in the top `AppBar` (`display: { xs: 'none', md: 'flex' }`), so they simply disappeared below the `md` breakpoint with no fallback. They now also render as individual rows inside the sidebar `Drawer` on mobile, grouped above the existing `sidebarCustomComponent` slot at the bottom of the sidebar. Desktop (`md+`) behavior is unchanged.

---

## [1.13.1] — 2026-07-09

### Changed

- **Optimized logo file sizes** — resized static logo assets to their actual display dimensions.

---

## [1.13.0] — 2026-07-09

### Added

- **Configurable learners-per-organization cap** — `Organization.get_learners_cap()`/`can_enroll_learner()` let you cap how many learners an organization can enroll, enforced in `EnrollCommand.execute()` across every enrollment path (platform, public, OAuth group enrollment, IMAP). Defaults to unlimited via `DJANGO_EMAIL_LEARNING["LEARNERS"]["MAX_LEARNERS_PER_ORGANIZATION"]`; set `LEARNERS_CAP_RESOLVER` to a dotted path to a `callable(organization) -> int` for custom per-organization logic (e.g. tiered plans). Exposed as a boolean only — `can_enroll_learner` in the platform organization API and `enrollmentOpen` in the public `appContext` — so clients can gate the UI without leaking capacity numbers.

---

## [1.12.0] — 2026-07-08

### Added

- **`can_add_member` feature flag and hook** — mirrors `can_create_course`: a `can_add_member` entry is included in `appContext.availableFeatures` by default (overridable by subclassing `get_available_features()`), and a new `OrganizationMemberCreationMixin.can_add_member()` hook (default `True`, overridable) is checked before creating an organization member via the API, with its result echoed back in the response. The "Add User" button on the organization page is disabled with a tooltip when not allowed.

---

## [1.11.2] — 2026-07-08

### Fixed

- **Organization member management security** — the role/profile update endpoint (`POST /organizations/<id>/users/<user_id>/`) had no authorization check at all; it now correctly requires the admin role, matching the existing delete endpoint.
- **Self-removal/self-demotion prevention** — an organization admin can no longer remove their own membership or change their own role. They can still update their own display name and photo. Another admin must perform those actions instead.

---

## [1.11.1] — 2026-07-06

### Added

- **Member avatars in the organization Members table** — shows each member's photo if set, or a first-letter fallback otherwise, matching the existing Learners table.

---

## [1.11.0] — 2026-07-06

### Added

- **`NEWSLETTERS.FROM_DOMAIN` setting** — generates a per-organization newsletter sender address (`<snake_cased_organization_name>@<FROM_DOMAIN>`, with the organization's name as the display name) instead of sending every newsletter from the same fixed address. Overrides `NEWSLETTERS.FROM_EMAIL` and the top-level `FROM_EMAIL` when set.

---

## [1.10.3] — 2026-07-05

### Fixed

- **Sidebar navigation** — the light/dark theme toggle moved out of the top navbar into its own "Appearance" section in the sidebar, with outlined icons.

---

## [1.10.2] — 2026-07-05

### Fixed

- **Analytics downloads** — CSV download buttons are now disabled when there's no data to export instead of producing an empty file.

---

## [1.10.1] — 2026-07-05

### Fixed

- **Course public page** — no-image courses now show a placeholder instead of hiding the title/enroll button, and the organization info box no longer leaves an empty column when there's no logo.
- **Organization logo removal** — removing an existing organization logo and saving now actually clears it on the backend.

---

## [1.10.0] — 2026-07-05

### Changed

- **Public organization/course page UX polish** — smaller layout, copy, and styling improvements across the public organization and course pages (course card image placeholder, enrollment button state, social link buttons, header layout, and related spacing fixes).

---

## [1.9.0] — 2026-07-05

### Added

- **Public course page link on the course detail page** — when a course is enabled, public, and belongs to a public organization, its page now shows a "Public page" button (with a globe icon) that opens the course's public page in a new tab, plus a copy-link icon to copy the URL directly. Backed by a new `Course.public_url` model property, mirroring the existing `Organization.public_url`.
- **Public-organization guard on the "Public Course" toggle** — the course form now forces "Public Course" off and disables the toggle when the organization itself isn't public, since a course can't be publicly reachable in that case. The new `organizationIsPublic` flag is exposed on the shared platform `appContext`.
- **Clearer form guidance** — the external references helper text now explains that these links are shown to learners on the course's public page before they enroll, and the course form gained divider separators between the References, IMAP Connection, Newsletter, and Upload Image sections for visual consistency.

---

## [1.8.0] — 2026-07-04

### Added

- **`PRIVATE_FILE_STORAGE_ALIAS` setting** — private files can now be backed by a completely different storage backend than public media (e.g. a separate S3 bucket), by pointing this setting at an entry in the project's own `STORAGES` setting. Previously, `PRIVATE_FILE_STORAGE_LOCATION` only let you change the path within a hard-coded `FileSystemStorage`, with no way to use S3/GCS/Azure for private files. `PRIVATE_FILE_STORAGE_LOCATION` remains the default when no alias is set.

---

## [1.7.1] — 2026-07-03

### Added

- **"enable it" only links when the course has content** — the single-course page's disabled-course banner now renders "enable it" as a clickable link only when the course actually has at least one piece of content; otherwise it's plain text, since enabling would just fail the existing "no content" guard.

### Fixed

- **`isInstructor` context now matches `can_act_as_instructor()`** — `BasePlatformView`'s `appContext.isInstructor` previously ran its own inline `role="instructor"` check, diverging from `OrganizationUser.can_act_as_instructor()` (used everywhere else), which also requires a `display_name` and additionally covers admins. Also removed an unused `isInstructore` typo in `Course.jsx` that was dead code.

---

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
