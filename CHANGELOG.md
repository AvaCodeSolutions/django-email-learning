# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [2.2.0] — 2026-07-18

### Added

- **7 new `SocialLink` platforms** — Facebook, Instagram, TikTok, X (Twitter), WhatsApp Channel, Telegram Channel, and Substack, alongside the existing Website/YouTube/LinkedIn. Purely additive (existing data untouched). Available in both the platform admin organization form and the public organization page. See [#733](https://github.com/AvaCodeSolutions/django-email-learning/issues/733).

### Changed

- **Public organization page social links redesigned** — replaced the outlined text+icon buttons with compact circular icon-only buttons (label shown as a tooltip on hover), centered on mobile. Each icon now hovers to its own brand color instead of a generic accent color.

## [2.1.4] — 2026-07-16

### Changed

- **Course form tooltip UX on mobile** — the slug field's explanatory tooltip no longer relies on hover (unclear/inconsistent on touch); it now shows as helper text under the field while focused, and clears on blur. All tooltips in the course form (slug, IMAP connection, newsletter, instructors) now open on click/tap instead of hover or touch-hold. The three icon-only info buttons also gained an `aria-label`, since they previously had no accessible name at all.

## [2.1.3] — 2026-07-16

### Added

- **Course slug auto-populates from the title when creating a course** — the slug field now live-derives from the title as you type (lowercased, hyphenated, capped at 50 characters), until you edit the slug field directly, at which point auto-sync stops and the slug stays exactly as typed. Edit mode is unaffected — the slug field there was already locked once a course exists. See [#730](https://github.com/AvaCodeSolutions/django-email-learning/issues/730).

## [2.1.2] — 2026-07-16

### Fixed

- **Organization logo deleted on every unrelated field update** — `OrganizationForm`'s local logo state was never seeded from the organization's existing logo, so it was indistinguishable from "user explicitly removed the logo." Saving any change (name, description, `is_public`, social links) on an organization that already had a logo silently wiped it. Fixed by seeding from the existing logo path and only signaling a change when it actually differs from that baseline, matching the pattern already used for course images. See [#725](https://github.com/AvaCodeSolutions/django-email-learning/issues/725).

## [2.1.1] — 2026-07-16

### Changed

- **Platform UI restyle** — no functional/API changes, visual only:
  - Primary color changed from purple (`#7c86ff`) to indigo (`#4f46e5`); several places that had the old purple hardcoded as a literal instead of a theme reference were fixed to track the theme color going forward.
  - Sidebar: the active nav item no longer renders as a clickable link when it's the exact current page (still highlighted, and still a link, when a sub-page of that section is active); lighter active/hover backgrounds; icon color now derives from the surrounding text color instead of a fixed purple.
  - Buttons: dropped the gradient hover overlay on contained buttons in favor of a flat color that darkens on hover; increased default padding.
  - Tables: removed alternating row stripes in favor of one flat light-gray tint for all rows; header is now white/bold in light mode instead of purple-tinted.
  - Public organization/course pages: hero boxes and the newsletter subscription box switched from a light-purple wash to light gray, and the newsletter box's email field/submit button are now a single attached control; mobile-only centering fixes for the org logo, org name, and course card enroll buttons.

## [2.1.0] — 2026-07-16

### Changed

- **`Organization.website`/`youtube_channel`/`linkedin_page` replaced by a `SocialLink` model** — these three fixed `URLField`s are gone; social links are now stored as `SocialLink` rows (`organization` FK, `platform` enum currently `website`/`youtube`/`linkedin`, `url`), so adding a new platform in the future is just a new enum choice rather than a schema change.
  - `GET`/`POST` responses for `/api/platform/organizations/` and `/api/platform/organizations/<id>/`, and the public organization/course pages, now return `social_links: [{platform, url}, ...]` instead of the flat `website`/`youtube_channel`/`linkedin_page` fields. The bundled platform admin form and public organization page (both included in this package) are updated to match.
  - `POST` requests to create or update an organization now take `social_links: [{platform, url}, ...]` instead of the three flat fields. On update, omitting `social_links` leaves existing links untouched; passing a list fully replaces them.
  - Existing data is migrated automatically: a data migration backfills `SocialLink` rows from the old fields before they're dropped, so no manual backfill step is needed when upgrading.
  - The platform admin organization form and the public organization page now render a generic, repeatable list of social links instead of three hardcoded fields.
  - See [#722](https://github.com/AvaCodeSolutions/django-email-learning/issues/722) for the full design rationale.

## [2.0.1] — 2026-07-16

### Fixed

- **Missing OAuth scope for Google group enrollment** — `GoogleGroupEnrollmentHandler` requested `admin.directory.user.readonly` and `admin.directory.group.readonly` but not `admin.directory.group.member.readonly`, which is required to read group membership. Added the missing scope.

## [2.0.0] — 2026-07-15

### Changed

- **Job-trigger HTTP endpoints now run asynchronously** — `deliver_contents`, `check_imap_connections`, `send_quiz_reminders`, `deactivate_inactive_enrollments`, and `send_newsletters` now hand the job off to a pluggable executor instead of running it inline and blocking the request until it finishes. This is a breaking change to the response contract of all five endpoints:
  - A successful trigger now returns `202` immediately with a `job_execution_id`, before the job has actually finished. Job success/failure is **no longer reflected in the trigger response** — poll the new `GET /api/jobs/executions/<job_execution_id>/` endpoint instead.
  - Hitting an endpoint while that job is already running now returns `409` with the `job_execution_id` of the in-progress execution, instead of silently returning `202` without doing anything (the previous, undocumented behavior).
  - `500` is now reserved for the rare case where the job couldn't even be handed off to the executor (e.g. the configured backend is unreachable), rather than the job itself failing.
  - By default, jobs run on an in-process `ThreadPoolExecutor` (size configurable via the new `JOB_EXECUTOR_MAX_WORKERS` setting, default `4`). Library users can plug in Celery, RQ, Django-Q, or another backend by implementing `JobExecutorProtocol` (`django_email_learning.ports.job_executor_protocol`) and pointing the new `JOB_EXECUTOR` setting at it — see the installation docs.
  - See the [async job execution issue](https://github.com/AvaCodeSolutions/django-email-learning/issues/720) for the full design rationale.

### Added

- **New `GET /api/jobs/executions/<job_execution_id>/` endpoint** — returns `job_name`, `status` (`running`/`completed`/`failed`/`stale`), `started_at`, `finished_at`, and `error` for a specific job execution. Use this to check the outcome of a job triggered via the endpoints above.
- **`JobStatus.FAILED`** and a new `JobExecution.error` field — a job that raises now gets an explicit `failed` row with the exception message attached, instead of being left at `running` until the 2-hour staleness sweep reclassifies it as `stale`. Requires a new migration.
- **`JOB_EXECUTOR` / `JOB_EXECUTOR_MAX_WORKERS` settings** — see above.

## [1.19.0] — 2026-07-14

### Fixed

- **Stored XSS via unsanitized user text on public pages** — `Course.description`/`target_audience`, `Organization.description`, and `Certificate.name_on_certificate` are plain-text-intended fields (no rich-text editor exists for any of them) but were rendered via `dangerouslySetInnerHTML` on public, unauthenticated pages with no sanitization at any layer. A payload like `<img src=x onerror=alert(document.cookie)>` executed immediately for any visitor — including on the same page as the public enrollment form. Fixed at both layers: a new `strip_html()` helper strips all markup at write time (pydantic validators for `Course`/`Organization`, and `SubmitCertificateFormView`), and the affected React components (`Course.jsx`, `Organization.jsx`, `Certificate.jsx`) now use plain JSX interpolation instead of `dangerouslySetInnerHTML`, as defense in depth. Also fixed a JSON-LD script-tag injection on the same public course/organization pages: `json.dumps()` doesn't escape `<`/`>`, so a description containing `</script><script>...</script>` could close the JSON-LD `<script>` block early regardless of JSON string quoting; the JSON is now escaped the same way Django's `json_script` template filter does. See [GHSA-w7h2-pp89-53q3](https://github.com/AvaCodeSolutions/django-email-learning/security/advisories/GHSA-w7h2-pp89-53q3).
- **No server-side sanitization on rich-text fields** — `Lesson.content` and `Sendout.body` are genuinely HTML-intended (both use the `ContentEditor` rich-text editor), but the API accepted whatever HTML was POSTed with no validation, so the editor's own UI restrictions could be bypassed with a direct request. Added a `sanitize_rich_text()` helper, an allowlist restricted to the tags/attributes the editor actually produces — paragraphs, headings, bold/italic, links, images (including width/height), lists, blockquotes, code blocks, and `text-align` styling — stripping `script`/`iframe`/`on*` attributes/`javascript:` hrefs/arbitrary CSS regardless of what's submitted.

---

## [1.18.0] — 2026-07-13

### Fixed

- **Cross-organization IDOR across course, learner, assignment, and organization-membership API views** — several API views verified the requester belongs to the `organization_id` in the URL, but then fetched the actual object (a `Course`, `CourseContent`, `Learner`, `Enrollment`, `AssignmentSubmission`, or `OrganizationUser`) by its own ID alone, without checking it belonged to that organization. This let a member of one organization read, modify, or delete another organization's data by substituting a different ID:
  - `SingleCourseView`, `CourseContentView`, `ReorderCourseContentView`, and `SingleCourseContentView` now scope every `Course`/`CourseContent` lookup by `organization_id`. The two delete paths were the most severe — any editor/instructor/admin of their own organization could previously delete another organization's entire course or any content item in it.
  - `SingleOrganizationUserView.delete` now scopes by `organization_id`, closing a path that let an organization admin remove any user's membership from *any other* organization.
  - `GetOrCreateUserByEmail` now authorizes against the organization named in the request body instead of the requester's own active organization, closing a path that let an org admin trigger an invite/password-reset email that named an organization they have no relationship to.
  - `SingleLearnerView`, `EnrollmentView`, and `EnrollmentsStatisticsView` now scope their queries by `organization_id`.
  - `SubmittedAssignmentDetailView` now scopes by `organization_id` and `course_id`.

  See [GHSA-q8c3-pjqw-h7rw](https://github.com/AvaCodeSolutions/django-email-learning/security/advisories/GHSA-q8c3-pjqw-h7rw).

---

## [1.17.0] — 2026-07-13

### Fixed

- **Cross-organization course access (IDOR) on the course detail page** — `CourseView` didn't verify that the requested `course_id` belonged to an organization the requester is a member of, so any authenticated member of any organization could view another organization's course details by changing the ID in the URL. `is_an_organization_member()` now requires an explicit way to resolve which organization a request should be checked against — either an `organization_id` in the URL, or a `resolve_org_id` callable that looks up the requested object's owning organization — and fails closed (403) instead of silently falling back to an organization the requester happens to belong to. See [GHSA-6w35-hmhh-pv63](https://github.com/AvaCodeSolutions/django-email-learning/security/advisories/GHSA-6w35-hmhh-pv63).
- **Removed the "first org membership" fallback from `is_an_organization_member()`** — views that authorize against the requester's active organization rather than a specific object (`Learners`, `Analytics`, the organizations list, `PrivateFileView`, `JobsStatus`, the session-update endpoint) previously fell back to an arbitrary org membership if the session hadn't been seeded yet, which isn't necessarily the org the requester is actually working in. This fallback now only ever consults the session and denies the request if it's empty, rather than guessing. If your app's login redirect lands directly on one of those views instead of a page that populates the session first (e.g. the courses list), that first request may now get a 403 — redirect through a page that sets `active_organization_id` first, or set it explicitly before those requests.

---

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
