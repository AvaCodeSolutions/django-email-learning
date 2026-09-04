# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changes prior to v1.0.0 are available in the [git history](https://github.com/AvaCodeSolutions/django-email-learning/commits/master).

## [6.1.0] - 2026-08-31

### Added

- **Injection-hardening validation for organization and course names** — `Organization.name` and `Course.title` are rendered verbatim into emails (subject lines, `From` headers, footers), so both now reject values that contain an `http(s)://` URL, newlines/control characters or Unicode line separators, zero-width and bidirectional-formatting characters, or a mix of scripts typical of homoglyph attacks (e.g. a Cyrillic "о" inside a Latin word). Every check runs against the NFKC-normalized form so compatibility look-alikes (`ｈｔｔｐ`) cannot slip past. `Organization.name` additionally caps at 60 characters (migration `0025`; the column shrinks from `max_length=200`). Enforced at the model layer (`full_clean()`), surfaced as `400`s by the platform organization API, and mirrored by a 60-character cap on the organization form's name field.

- **Per-course organization branding in email footers** — a new **Show organization branding in email footer** toggle on the course form (off by default) adds the organization's logo (when set), name and social links to the footer of every course-scoped email: lessons, quizzes, assignments, both reminder types, assignment reviews, enrollment verification, certificate finalization, and deadline-deactivation notices. Applies to the HTML part of each email only; the plain-text and AMP alternatives are unchanged. Backed by the additive `Course.show_organization_footer` field (migration `0024`, default `False`, no backfill). The social links render as plain text links, shared with newsletter sendouts via `emails/_social_links.html`.
- Newsletter email footers now render social links as plain text links too. The previous inline-SVG icons rendered blank in Gmail, which strips `<svg>` from HTML email.

### Changed

- The **"Powered by Django Email Learning"** email footer credit moved from `emails/lesson.html` into a `{% block credit %}` in `emails/base.html`, so it now appears on every base email (course content, reminders, enrollment, certificate, password reset) and library users can override or remove it by overriding `{% block credit %}` (or the whole `{% block footer %}`). Newsletter sendouts opt out of the base footer entirely.

## [6.0.2] - 2026-08-31

### Fixed

- **Deleting course content that learners had already reached silently destroyed their data and stranded them mid-course** — `DELETE /organizations/<id>/courses/<id>/course-contents/<id>/` called `CourseContent.delete()` with no guard, so Django cascaded through every `ContentDelivery` for that content: pending `DeliverySchedule` rows vanished without being marked `CANCELED`, learners' quiz/assignment submissions and their feedback were permanently deleted, delivery history disappeared from analytics, and any learner sitting on that content stopped progressing because the `ContentDelivery` that would have triggered the next one was gone. `CourseContent.delete()` now refuses (HTTP 409) once any `ContentDelivery` references the content; the message points the caller to unpublish instead. Content that no learner has reached still deletes normally. The course page now surfaces the rejection (and any other delete failure) as an error alert instead of only logging it to the console.
- **Unpublishing content mid-course stranded learners sitting on it** — `DeliverContentsJob.process_delivery` canceled the delivery for unpublished content but never scheduled what came next, so the enrollment stalled forever. It now skips the unpublished content the same way a delivered lesson advances the learner: the next published content is scheduled, or the enrollment graduates if there is none. This makes "unpublish" the safe way to pull content out of a running course.

## [6.0.1] - 2026-08-31

### Fixed

- **Deadline-less quiz/assignment reminders now actually recur** — `reminder_interval_days` is documented as "send reminder emails every N days", but `SendRemindersJob` marked `reminder_state = SENT` after the first send and nothing ever re-armed it, so a learner who never attempted the quiz got exactly one reminder, N days after delivery. For content with **no deadline** (`deadline_days = 0`) and a positive `reminder_interval_days`, a successful send now re-arms `remind_at` for another nudge N days later, up to a cap of **3 reminder emails** total (`ContentDelivery.MAX_RECURRING_REMINDERS`), after which the delivery settles in `SENT`. Submitting, graduating or failing still flips `reminder_state` to `NOT_APPLICABLE` and stops the reminders early. Content **with** a deadline is unchanged: a single reminder, sent one day before the deadline (ten hours before for a one-day deadline).
- **Reminder for the second quiz attempt was never sent** — When a learner failed a `limited_attempts` quiz for the first time, the retry delivery recomputed `remind_at` but left `reminder_state` at `NOT_APPLICABLE` (set earlier in the submission handler), so the reminder queue — which only picks up `PENDING` rows — skipped it. The retry now re-arms the reminder (`reminder_state = PENDING`, `reminder_count` reset to 0) whenever a new `remind_at` is scheduled.

### Changed

- **New `ContentDelivery.reminder_count` field** (migration `0023`) tracks how many reminder emails a delivery has received, backing the 3-reminder cap. Additive column with a default of `0`; no data backfill required.
- The `reminder_interval_days` help text on `Quiz` and `Assignment`, and the **Reminder Interval Days** tooltip in the course form, now state that at most 3 reminders are sent and that they stop once the learner completes the item.

## [6.0.0] - 2026-08-30

### Added

- **Per-course "From" address** — A course can now send its content from its organization's own address instead of the platform-wide `DJANGO_EMAIL_LEARNING["FROM_EMAIL"]`. The course create/edit form gets a **Send course emails from** selector with **Platform default** and **Organization address**; the second shows a live preview of the resulting address (`<Organization Name> <org-slug-<id>@your-domain>`) and is disabled, with an explanation, until the installation opts in. Opting in is a single new setting, `DJANGO_EMAIL_LEARNING["DOMAIN_WIDE_EMAIL"] = {"ENABLED": True, "DOMAIN": "learn.example.com"}` — turn it on only once SPF/DKIM/DMARC authorise your mail service to send for any local part on that domain. When enabled, the organization address is used for every course-scoped email: lessons, quizzes, assignments, reminders, assignment reviews, certificate finalization, enrollment verification and confirmation, and deadline-deactivation notices. The stored per-course choice is never rewritten — disabling the switch transparently falls back to `FROM_EMAIL`, and re-enabling it restores the organization address. The organization's local part includes its id because organization names are not unique. The AMP quiz-submission origin check now also trusts any sender at the configured domain. If you send AMP (dynamic) emails, note that Gmail's dynamic-email registration is per-domain, so the organization domain must be registered separately from your default `FROM_EMAIL` domain.

### Changed

- **BREAKING: `NEWSLETTERS.FROM_DOMAIN` removed** — Newsletter sendouts now share the new top-level `DOMAIN_WIDE_EMAIL` switch with course content instead of their own `NEWSLETTERS.FROM_DOMAIN` setting. When `DOMAIN_WIDE_EMAIL` is enabled, sendouts are sent from the organization address; otherwise they fall back to `NEWSLETTERS.FROM_EMAIL`, then the top-level `FROM_EMAIL`, then `webmaster@localhost` as before. The generated local part also changes: it is now `organization-slug-<id>` (e.g. `acme-inc-7`) rather than the previous `snake_cased_name` (`acme_inc`), which fixes newsletter senders from different organizations sharing an address when their names matched. Deployments using `NEWSLETTERS.FROM_DOMAIN` must move the domain to `DJANGO_EMAIL_LEARNING["DOMAIN_WIDE_EMAIL"]` and re-verify any address allow-lists.

## [5.5.3] - 2026-08-29

### Fixed

- **Course unsubscribe confirmation rejected real submissions from Safari** — 5.5.2's confirmation gate required the request to carry `Sec-Fetch-User: ?1`, but Safari never sends that header (it implements `Sec-Fetch-Site`/`Mode`/`Dest` only), so ticking the box and choosing **Unsubscribe** in Safari just redisplayed the "please tick the box" message. The required checkbox is now the sole human gate; Fetch Metadata is used only to reject clearly automated submissions — a cross-site origin, or a scripted `fetch()`/XHR instead of a same-origin form navigation.
- **Confirmation checkbox and its label now sit on one line** — the checkbox is wrapped in a centered flex row instead of a full-width block, so the box and "Yes, unsubscribe me from this course" render together rather than stacked.

## [5.5.2] - 2026-08-29

### Security

- **Course unsubscribe now requires a genuine human confirmation** — Moving the unsubscribe mutation to a `POST` (5.x) stopped plain link-fetchers, but not JS-executing email link scanners and headless-browser mail sandboxes, which render the confirmation page and submit its form anyway — silently unsubscribing learners who never clicked. The confirm form now carries a required checkbox, so `UnsubscribeView.post` only unsubscribes when it is ticked; submissions whose Fetch Metadata headers show a cross-site origin or a scripted `fetch()`/XHR (rather than a same-origin form navigation) are rejected outright. Anything rejected re-renders the confirmation page and changes nothing. The confirm button is relabelled "Unsubscribe" so consent-autoclicker browser extensions stop matching it.
- **Unsubscribe token kept out of the confirm request's `Referer`** — The unsubscribe pages now send `Referrer-Policy: strict-origin`, so the confirm `POST` no longer carries the JWT from the emailed link in its `Referer` header, where it was landing in access logs and traces. The token still appears once in the initial `GET` URL — redact that at the CDN/log-ingestion layer.

## [5.5.1] - 2026-08-29

### Fixed

- **Enrolling a learner who was previously cancelled on the same course no longer 500s** — The manual enrollment endpoint (`POST /api/platform/organizations/<id>/courses/<id>/enrollments/`) re-fetched the enrollment it had just created with a lookup by learner email and course. A learner who had a deactivated enrollment for that course — from an earlier admin cancellation or self-unsubscribe — still has that row on file, so the lookup matched two enrollments and raised `MultipleObjectsReturned`. The lookup now excludes deactivated enrollments, so re-enrolling such a learner succeeds and returns the new active enrollment.

## [5.5.0] - 2026-08-28

### Added

- **Course Info tab on the platform course page** — The course detail page gets a new **Course Info** tab (after **Course Analytics**) that shows the full course settings form — title, description, target audience, language, public and certificate switches, external references, IMAP connection, newsletter link, instructors and course image — without leaving the page to open the edit dialog. It opens read-only: every field is disabled and the sub-forms for IMAP, newsletter and instructors are non-interactive, so it reads as a summary. A pencil (edit) button in the top-right toggles the form into an editable state with **Cancel** and **Update** buttons; saving, cancelling, or switching to another tab returns it to read-only. The slug stays disabled throughout, since it can never be changed after creation.

### Fixed

- **`CourseForm` locale keys were missing from the course detail page** — Rendering the course settings form on the course detail page (for the new tab) hit a `TypeError` because `CourseView.get_locale_messages()` did not provide the keys `CourseForm` relies on. All of the form's locale keys are now included in the course detail view's context, along with the new tab labels and the "Course updated successfully." confirmation message.

## [5.4.0] - 2026-08-28

### Added

- **The public course page lists its instructors** — When a course has instructors assigned, their names and photos now appear on the course's public page as a bordered, divided list under an **Instructors** heading, between the course info and the topics list — matching the existing "Topics covered" and "External References" sections. An instructor without a photo gets an initial-letter avatar in the organization's brand colour. Courses with no instructors are unchanged. The instructor name shown is the display name set on the organization membership.

### Fixed

- **Editing a course that has instructors no longer fails with a 400** — The platform course API returned each instructor as `{display_name, photo}` with no id, so the edit form could not round-trip the assigned instructors and sent `null` ids back on save, which the update endpoint rejected. `InstructorResponse` now includes the `OrganizationUser` id, the form filters out any missing ids, and the course edit form submits a valid instructor list.

## [5.3.0] - 2026-08-28

### Changed

- **The organization page opens on General Info** — It opened on Members, which is the tab an admin is least likely to want first: the page's own identity — name, description, logo, public page — lived one click away behind a tab that, for most organizations, lists a handful of people who rarely change. General Info is now the tab you land on. Links that name a tab explicitly are unaffected, including the dashboard's setup shortcuts and the newsletter breadcrumbs.
- **`?tab=` is validated before it selects a tab** — The organization page already accepted a `tab` query parameter, but took whatever the URL said. A misspelled name, or `?tab=api_keys` from someone without the organization API feature, selected a tab that was not on the page: an empty panel below a tab strip with nothing highlighted. The parameter is now checked against the tabs that actually render for that user, and anything else falls back to General Info. Accepted values are `general_info`, `members`, `newsletters`, and `api_keys`.

## [5.2.1] - 2026-08-25

### Security

- **`nanoid` updated to 3.3.18** — Picks up the fix for [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8) (high): a custom generator could loop indefinitely when asked for a size of zero. It reaches the project as a transitive dependency of `postcss`, which Vite uses to build the frontend, so it is a build-time dependency only and never ships in the served assets. `npm audit` on the frontend now reports no vulnerabilities.

## [5.2.0] - 2026-08-25

> **Upgrading.** Run the migrations. The only schema change is a new choice on the enrollment deactivation reason; nothing existing is rewritten.

### Added

- **Cancel a learner's enrollment from the Learners page** — Organization admins get a **Cancel enrollment** button in the enrollment dialog's header, for enrollments that are still running. Cancelling deactivates the enrollment and cancels every content delivery still scheduled for that learner, so the course stops arriving in their inbox — a delivery already being sent is left alone, since that email is on its way either way. The learner is not notified, and can be enrolled in the same course again afterwards, which leaves the cancelled enrollment in place as a record. The action asks for confirmation first, because the enrollment state machine has no way back out of deactivated. Behind it is a new admin-only endpoint, `POST /api/platform/organizations/<id>/enrollments/<id>/cancel/`, which returns `409` and changes nothing if the enrollment reached a final state in the meantime.
- **`revoked` deactivation reason** — A cancellation by an admin is recorded as `revoked` rather than reusing `canceled`, which means the learner unsubscribed themselves. Both end the enrollment, but the enrollment timeline and the `user_enrollment_deactivated` metric — which is broken down by reason — can now tell "we cut this learner off" from "this learner opted out". Existing rows keep whatever reason they already had.

## [5.1.2] - 2026-08-19

> **Upgrading.** Run the migrations. Deliveries stranded in `processing` by the bugs below are returned to the queue by the first `deliver_contents` run after you upgrade, and go out on the run after that — nothing to clean up by hand.

### Fixed

- **Content deliveries could get stuck in `processing` and never be sent** — A delivery schedule is moved to `processing` before its email is sent, and moved out of it by whatever happens next — delivered, canceled, rescheduled, blocked. The queue only ever looks for `scheduled` rows, so any path that claimed a schedule without finishing it hid that delivery from every later job run, silently and for good: no error, no retry, and the job still reporting success. The learner simply stopped receiving their course. Four such paths are fixed. The delivery and reminder queues claimed a batch of due schedules while being *constructed*, and the jobs built their queue before checking whether another instance was already running — so two overlapping runs meant the second one claimed up to fifty schedules and then exited without touching any of them. Queue construction and claiming are now both deferred until the job actually starts pulling work. Sending a delivery by hand from the Learners page claimed the row before the block that guards the delivery, so an error while loading the schedule escaped with the row still claimed; the load now happens inside that guard and releases the claim. And a content row whose type had nothing to send returned without changing the status at all, leaving the schedule claimed with nothing logged — it is now blocked and counted in the blocked-delivery metric, rather than handed back to the job to fail on again every run.
- **A worker killed mid-delivery left its schedule claimed forever** — A process that dies between claiming a schedule and sending it — a deploy restarting the container, an OOM kill, a request killed by the web server's timeout — never gets to run any cleanup, so no amount of error handling releases the row. Schedules now record when they were claimed, and each `deliver_contents` run returns claims older than `STALE_CLAIM_HOURS` (default 2) to the queue, logging the ids it recovered. Deliveries that are genuinely in flight are never touched, including one being sent by hand from the Learners page.

### Added

- **`STALE_CLAIM_HOURS`** — Optional integer setting controlling how long a delivery may sit claimed before the `deliver_contents` job treats it as abandoned and requeues it. Defaults to `2` hours. Raise it if a single delivery can legitimately take longer than that to send.

## [5.1.1] - 2026-08-19

### Security

- Updated `cryptography` and `dompurify` to their latest versions to pick up upstream security fixes.

### Changed

- Routine dependency updates (Django/Python tooling, Vite, eslint, React ecosystem) — no functional changes.

## [5.1.0] - 2026-08-15

### Added

- **Send a learner's next content immediately from the Learners page** — The enrollment dialog now shows, under the course title, when the learner's next content is scheduled to arrive and which content it is, with a **send now** link beside it for organization admins. Sending runs the delivery there and then: the email goes out, the schedule is marked delivered, and the follow-up work happens exactly as it would during a job run — the next content is scheduled, or the enrollment graduates if that was the last one. Bringing the schedule's time forward was never equivalent, because the delivery job runs on a cron and the content would still wait for its next tick. Behind it is a new admin-only endpoint, `POST /api/platform/organizations/<id>/enrollments/<id>/delivery-schedules/<id>/send/`, and a `next_delivery` field on the enrollment detail response (`null` when nothing is scheduled). The schedule is claimed with the same `SCHEDULED → PROCESSING` compare-and-set the delivery queue uses, so a job run happening at the same moment cannot send the same content twice; a delivery that is no longer scheduled returns `409` and is left untouched, and one that fails to send is retried or blocked by the job's own retry logic.

## [5.0.0] - 2026-08-15

> **Upgrading.** No migrations. One thing to check before you upgrade: if you call `POST /api/v1/enrollments/` and rely on the learner receiving a verification link, add `"verified": false` to the request body — that is now opt-in, and the default creates the enrollment active instead. Callers that read `status` from the `201` response get `active` rather than `unverified`. Nothing else in the API changed.

### Changed

- **`POST /api/v1/enrollments/` creates a verified enrollment by default** (breaking) — The endpoint used to always create an `unverified` enrollment and email the learner a verification link, so nothing was delivered until they clicked it. It now creates the enrollment **active** by default: the first content is scheduled straight away and the learner gets the "enrollment verified" email that opens the course, with no verification link. This matches what a key-authenticated integration usually wants — the caller has already established the address in its own signup flow, and asking the learner to confirm a second time was a step nobody needed. A new `verified` field in the request body restores the old behaviour: send `"verified": false` to create the enrollment unverified and email the verification link, exactly as before. **Anything relying on the previous default needs to start sending `"verified": false`**, including code that reads `enrollment.status` from the `201` response — it is now `active` rather than `unverified`. One new failure mode comes with it: a verified enrollment can only be created for a course with at least one published content, since activation is what schedules the first delivery; enrolling into a course with nothing published returns `500` and creates nothing, so the call can be retried once the course has content. `subscribe_to_newsletter` still opts the learner in, and the subscription is now confirmed in the same request when the enrollment is created verified.

## [4.1.0] - 2026-08-08

### Added

- **`GET /api/v1/ping/` for checking an organization API key** — Returns `200` with `{"status": "ok"}` for any valid, non-revoked, unexpired organization key, and the usual `401`/`403` otherwise. It requires no scope, so an integrator can confirm its credential reaches the right deployment without holding a permission for an unrelated resource, and it reads and writes nothing. Rate limited per key like every other v1 endpoint.
- **The OpenAPI document's title is configurable** — Set `DJANGO_EMAIL_LEARNING["OPENAPI"]["TITLE"]` to replace the default `"Django Email Learning — Organization API"` in `GET /api/v1/openapi.json`, so a deployment serving the API under its own product name doesn't hand integrators a document titled after the library.

## [4.0.0] - 2026-08-07

> **Upgrading.** Run the migrations and you're done — existing API keys keep authenticating, because the backfill derives the new hash from the stored ciphertext and credentials issued before this release are still accepted. Two things to know before you upgrade. Keys can no longer be *read back*: the API Keys page now shows each key's id and status instead of the key itself, so anyone who has lost their key must issue a replacement. And if your own code imports `ApiKey` from `django_email_learning.models`, note that `key`, `salt`, `generate_key()` and the inherited `decrypt_password()` are gone — use `ApiKey.create()`, which returns the model and the one-time token together.

### Added

- **Organization API keys and a new organization-scoped API** — Organization admins can now issue API keys for their own organization via `POST /api/platform/organizations/<id>/api-keys/`, and use them against a new `/api/v1/` surface. v1 covers one endpoint, `POST /api/v1/enrollments/`, which enrolls an email address in one of the organization's courses. Keys carry explicit scopes — `enrollments:create` is the only one for now, and an organization key must carry at least one — plus an optional expiry. The organization is taken from the key itself rather than from the URL or request body, so a key can only ever act on the organization it was issued for; a slug or id belonging to another organization reads as `404`. Only organization *admins* can issue keys, since a key acts with whatever scopes it carries. Requests are rate limited per key (defaults 120/60s, configurable via `DJANGO_EMAIL_LEARNING["ORGANIZATION_API_RATE_LIMITS"]`). This is separate from the existing unauthenticated `/api/public/` embed surface. Keys are managed from a new **API Keys** tab on the organization page, which lists each key's id, scopes, status and last use, and shows the key itself only once, at creation. See the new [Organization API](https://django-email-learning.readthedocs.io/en/latest/technical/organization-api.html) reference.
- **`ORGANIZATION_API` platform feature and permission hooks for key management** — A new `PlatformFeature.ORGANIZATION_API`, present by default, controls whether the organization page shows its API Keys tab; remove it from `get_available_features()` to hide it. The API side has its own control: override `can_create_organization_api_key(request, organization)` on `OrganizationApiKeyView` or `can_delete_organization_api_key(request, organization)` on `SingleOrganizationApiKeyView`. Both default to `True` and reject with `403` before any database work when they return `False`, following the same pattern as the existing `can_create_course` hook. They receive the resolved `Organization` rather than its id, so a check can read its state without a second query.
- **OpenAPI 3.1 schema for the organization API** — `GET /api/v1/openapi.json` serves a machine-readable description of the v1 API for Swagger UI, Redoc or a client generator. It takes no API key, since it describes the API's shape and carries no organization data; set `DJANGO_EMAIL_LEARNING["ORGANIZATION_API_DOCS_ENABLED"] = False` to stop serving it. The document is generated from the running code rather than maintained separately — paths from the URLconf, schemas from the Pydantic models the views validate with, and security requirements from the scopes the auth decorator enforces — and a test fails the build if a routed endpoint has no documentation. No new dependency.
- **API keys now support naming, expiry, revocation and last-used tracking** — Both platform and organization keys take a `name` and an optional `expires_at`, record `last_used_at` on each authenticated request (at minute resolution, so recording activity doesn't cost a write per request), and can be revoked.

### Security

- **API keys are stored hashed instead of reversibly encrypted** (breaking) — Keys were held as Fernet ciphertext under `ENCRYPTION_SECRET_KEY`, which meant anyone with the database and that setting could recover every key in plaintext; the listing endpoint and the settings UI both did exactly that on every page load. Keys are now stored as a SHA-256 hash of a 256-bit random secret and the full token is returned **once**, at creation. The token format is `elk_<key_id>_<secret>`, where `key_id` is a non-secret public identifier that makes verification a single indexed lookup instead of decrypting every candidate row. **Existing keys keep working** — a data migration derives the new hash from the stored ciphertext, and the pre-4.0.0 JWT resolves through the same lookup — but they can no longer be *read back*: the API Keys page now shows each key's `key_id` and status rather than the key itself, and an operator who has lost a key must issue a replacement. Support for the legacy JWT format will be removed in a future release.
- **The JWT wrapper around API keys is no longer issued** (breaking) — Keys were handed out as a JWT signed with `JWT_SECRET_KEY` and a fixed `exp` of `datetime.max`. It never expired and carried no claim that wasn't already the credential; its only real function was smuggling the row's `salt` to narrow the old decrypt-and-compare lookup, which the new `key_id` does directly. New keys are issued as the bare token. Existing JWTs are still accepted.
- **Organization keys cannot reach platform endpoints, and vice versa** — The two kinds are distinguished by an explicit `key_type` column with a database check constraint tying it to the presence of an organization, rather than by inferring "platform" from the organization being null. A dropped filter therefore cannot silently produce a key with deployment-wide authority; `check_api_key` asserts the platform type positively, and the job-trigger endpoints return `403` for an organization key.

### Changed

- **`POST /api/platform/api_keys/` returns `token` instead of `key`** (breaking) — The creation response now carries the full token as `token`, alongside metadata including `key_id`, `name`, `key_type`, `scopes`, `expires_at`, `revoked_at` and `last_used_at`. `GET /api/platform/api_keys/` returns that same metadata and **never** returns a usable credential; it is also now filtered to platform keys only. Anything reading `key` from either response needs updating.
- **`DELETE /api/platform/api_keys/<id>/` revokes rather than deletes** (breaking) — The row is retained with `revoked_at` set, so the audit trail of which keys existed and when each was last used survives. The response message changed from `"API Key deleted successfully"` to `"API Key revoked successfully"`. Revoked keys fail authentication with `401`.
- **`rotate_encryption_key` no longer processes API keys** — Hashes cannot be re-encrypted and do not need rotating. The command still rotates `ImapConnection.password`. Rotating `ENCRYPTION_SECRET_KEY` no longer invalidates API keys.

## [3.0.0] - 2026-08-05

> **A deliberately small major.** Nothing here requires a migration on the scale of 2.0.0 — for most projects the upgrade is a no-op. The major bump reflects that two changes alter behavior existing callers can observe, not that the release is large. Read the two entries below if you query organizations by name or render the `Organization` model directly.

### Changed

- **`Organization.name` is no longer unique** (breaking) — Global uniqueness on the organization name meant one tenant's choice of name blocked an unrelated tenant from using theirs, which is a real collision for organizations that genuinely share a name. Nothing in the library resolved an organization by name — URLs, permission checks and the active-organization session value are all keyed on `id` — so the constraint provided no isolation, only friction. Creating a second organization with an existing name now succeeds instead of returning `409`. Downstream code calling `Organization.objects.get(name=...)` should move to `id`, as it will raise `MultipleObjectsReturned` once duplicates exist. If you need a unique, human-readable handle for URLs, add a dedicated unique `slug` field rather than relying on `name`.
- **`Organization.__str__` now includes the id** (breaking) — Returns `"Acme (#3)"` rather than `"Acme"`, so same-named organizations stay distinguishable wherever a human picks one, such as admin foreign key dropdowns. Email templates and public pages are unaffected: they render `organization.name` directly rather than the model.

## [2.17.0] - 2026-08-03

### Added

- **1000-character limit on course and organization descriptions** — The `description` field on both models now enforces a maximum of 1000 characters, matching the API request/response schemas. The course and organization forms show a live "X/1000 characters used" counter and cap input at the limit; existing descriptions already over 1000 characters are unaffected until the record is next saved.

### Changed

- **`Course` and `Organization` now run full validation on save** (breaking) — Both models call `full_clean()` from `save()`, so invalid data now raises `ValidationError` at save time instead of either succeeding silently or surfacing later as a raw `IntegrityError` (a duplicate `embed_token`, for example, used to raise `IntegrityError` and now raises `ValidationError`). Code that creates these models directly through the ORM, rather than through the API, must supply all required fields, including `Course.slug`.
- **Dependency updates** — `ruff` to 0.16.x, `django` to 6.0.7, `django-stubs` to 6.0.7, `pre-commit` to 4.6.1, and `pillow` to 12.3.0.

## [2.16.0] - 2026-08-03

### Security

- **Unsubscribe links unsubscribed on GET** (breaking) — Both unsubscribe flows performed their mutation from a `GET`, so anything that fetches a URL on the recipient's behalf — mail client link prefetching, corporate link scanners, chat previews — could silently unsubscribe them. The course unsubscribe page already showed a confirmation step, but confirming was a plain link to `?confirm=true`, which is still a `GET`; the mutation now lives in a CSRF-protected `POST` submitted by a form on that page, with the token moved from the query string into a form field. Newsletter unsubscribe had no confirmation at all and now serves a confirmation page on `GET`, deleting the subscriber only on `POST`. Newsletter sendouts additionally carry `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers so that mail clients honoring [RFC 8058](https://www.rfc-editor.org/rfc/rfc8058) unsubscribe via a one-click `POST` rather than following the link; the headers are only set when `SITE_BASE_URL` is configured. Anything linking to these URLs and expecting a `GET` to unsubscribe needs to issue a `POST` instead.
- **API error responses echoed exception detail** — Several endpoints returned `str(exception)` straight to the client: JWT decode failures on the personalised file-upload, assignment, quiz and certificate-form endpoints; blocked-email and learner-cap errors on enrollment; and the job execution status view, which returned the stored job error verbatim. Each now returns a fixed, generic message plus an `error_id`, with the real detail logged against that same id, so operators can still correlate a report to the underlying failure without exposing internals. Enrollment also gained a catch-all returning `500` with the same shape instead of propagating. Clients matching on error *strings* rather than status codes will need updating.
- **Updated `pyasn1` for CVE-2026-59884** — Bumped 0.6.2 to 0.6.4 in `poetry.lock`.

### Added

- **Public-profile notice on the dashboard** — The dashboard's "Complete your organization profile" setup item now shows an inline notice when the organization's profile page is public, with a link that opens the public page in a new tab. Previously nothing on the dashboard indicated whether that page was visible to the world.

### Changed

- **Frontend dependency updates** — `@testing-library/jest-dom` to v7, the TipTap monorepo to 3.29.2, `eslint` to 10.8.0, and `globals` to 17.8.0.
- **Removed `uv.lock`** — The project's lockfile is `poetry.lock`; `uv.lock` was a stray second lockfile that could drift from it. Deleted and added to `.gitignore`.

### Fixed

- **Enrollment verification subscribed learners who had not opted in** (breaking) — Verifying an enrollment auto-created a subscription to the course's linked newsletter for every learner, regardless of whether they ticked the newsletter checkbox at signup. Opt-in is decided at enrollment time via `subscribe_to_newsletter`, and verification now only *confirms* a subscription that already exists, rather than creating one. Learners auto-subscribed by the previous behavior are unaffected and remain subscribed; going forward, only those who opted in are added.

## [2.15.0] - 2026-08-01

### Security

- **URLs from the server-rendered app context reached the DOM unvalidated** — The frontend reads its configuration from the `#app-context` script tag, and a good deal of that is organization-editable (the organization logo and public link, course images, social links, the terms of service link, uploaded file URLs) or comes from deployment settings. Those values were being used directly as `href` and `src` attributes and as `fetch()` targets, so a stored `javascript:` or `data:text/html` URL would have run on click — on the public organization and course pages, that means against anonymous visitors. Added a shared `sanitizeUrl` module with three helpers (links, image sources, endpoint bases) and applied it to every app-context URL, to the server-response URLs reaching the same sinks (learner and instructor photos, lesson image and assignment file URLs, certificate links), and to the link and image URLs typed into the content editor, which are stored and re-rendered into lesson pages and emails. Sanitization rejects rather than rewrites, so legitimate URLs — including relative ones — are unchanged. No exploitation is known; this closes the class of defect rather than a specific report.

### Changed

- **Frontend linting works again and runs on commit** — `eslint .` had been failing immediately for every file: `eslint-plugin-react-hooks` 7 still ships its recommended config in the legacy eslintrc shape, which ESLint 10's flat config rejects outright. Pointed at the flat variant, excluded generated coverage reports from linting, and gave test files their Vitest and Node globals; the React Compiler diagnostics that `react-hooks` 7 newly enables are set to warnings for now, since existing components trip them widely. Added an `eslint` pre-commit hook that lints staged frontend files using the repo's own ESLint, so its version and plugins always match `package.json`; CI runs the same lint in the frontend job, which already has Node installed and only runs when `frontend/` changes. Also removed `frontend/src/render-callback.jsx`, which was unreferenced and would have thrown on load.

## [2.14.0] - 2026-07-30

### Changed

- **Job status is restricted to platform admins** (breaking) — `/api/platform/status/jobs/` was readable by any organization member and now requires a platform admin, returning `403` otherwise. The Dashboard's content delivery health card was gated only on having active courses, so organization members were being shown this data; both it and the sidebar indicator are now gated on the platform admin flag and skip the request entirely for everyone else. Any integration calling this endpoint with a non-platform-admin session needs to be updated.

### Fixed

- **Raw frontend source emitted into the build output** — `frontend/public` holds source entries rather than static assets, so Vite's default `publicDir` handling also copied it verbatim into `dist/`, producing raw `.jsx` files and unbuilt `index.html` next to the built assets. These were never packaged (only `dist/assets` ships), so this is build hygiene rather than a shipped-content change; built entries and manifest keys are unchanged.
- **`make frontend-dev` did not exist** — the target was misspelled `fronend-dev` while the help text advertised `frontend-dev`. Renamed, along with `start-dev`'s reference to it, and `.PHONY` corrected to match the actual targets.

## [2.13.2] - 2026-07-30

### Fixed

- **Course embed widget showed a broken image instead of no image** — With "Show course image" turned off (or for a course with no image at all), the widget rendered an `<img>` pointing at the embedding page's own URL rather than omitting the image. The embed script's image sanitizer resolved its input as a relative URL, and an empty value resolves to the host page instead of being rejected.

## [2.13.1] - 2026-07-30

### Changed

- **Job execution lookup index** — Added a composite index on `JobExecution` (`job_name`, `started_at` descending) so the "latest run per job" queries behind the job status views are served straight from the index instead of scanning and sorting.

## [2.13.0] - 2026-07-30

### Added

- **Organization Brand Color** - A new field for the organization is added to select the brand color which will be used in the organization and course public pages.

## [2.12.2] - 2026-07-29

### Fixed

- **Oversized headings on the public organization and course pages** — The global `h1`-`h3` styles use fluid `clamp()` sizing meant for marketing pages; pinned smaller, fixed font sizes locally on these two public pages instead.

## [2.12.1] - 2026-07-29

### Added

- **Dismissible Sponsor section** — The Dashboard's Sponsor card can now be closed with an X button in its top-right corner, in addition to removing it via `DASHBOARD.SECTIONS`. Dismissal is remembered in a cookie, so it stays hidden on future visits.

### Changed

- **Sponsor/Star button styling** — Both Dashboard buttons now share the same outlined style; the sponsor button keeps its pink accent on the heart icon only, and the GitHub icon on the star button is black.

## [2.12.0] - 2026-07-28

### Added

- **Sponsor dashboard section** — A new built-in `sponsor` section (added to the default `DASHBOARD.SECTIONS`) shows a small card on the Dashboard asking users to sponsor the project via GitHub Sponsors or star it on GitHub, with a note on how to remove it via config. Also documented `DASHBOARD.SECTIONS`/`DASHBOARD.CUSTOM_COMPONENTS`, which previously had no docs page.

## [2.11.1] - 2026-07-28

### Fixed

- **Certificate page broken by the new heading styles** — The certificate is a fixed-physical-size printable document (A4 landscape), but its title and description used `h1`/`h3`, which now carry the app-wide display font and viewport-relative fluid sizing. Pinned the certificate's typography back to its original fixed font and sizes.

## [2.11.0] - 2026-07-28

### Changed

- **Applied the AvaCode design system across the docs site and admin frontend** — Both now load Inter and Bricolage Grotesque, with headings set in the display font per the design system's type scale. The admin app's primary color and table row hover/default backgrounds were retinted to match, and the navbar/sidebar logo assets were regenerated in Bricolage Grotesque.

### Fixed

- **Docs site custom styles were never actually applied** — `docs/source/conf.py` was missing `html_static_path`, so `custom.css` 404'd silently and none of its rules ever took effect.
- **Dashboard nav item always showed as active** — its link is the platform section's root, so a path-prefix check incorrectly matched it against every other page under it.
- **Vite dev server font 404s** — font files loaded via `@fontsource` 404'd under Django's static path in dev mode.

## [2.10.3] - 2026-07-25

## Fixed

- **Enhanced Analytics page frontend** Changed the API calls to run in batches of 2 requests instead of all at once, since they can be database-heavy queries, and also fixed the version/API mismatch between MUI and X-Charts.

## [2.10.2] - 2026-07-24

### Fixed

- **Fixed the organization-member invitation email subject** — The subject now clearly indicates that the recipient has been added to an organization, rather than implying a password reset.

## [2.10.1] - 2026-07-24

### Fixed

- **Fix N+1 query causing slow analytics page loads** - Added extra indexes and fixed the N+1 query for progress percentage

## [2.10.0] — 2026-07-24

### Added

- **"Public page" button on the organization single page** — Mirrors the course page's implementation: a link to the organization's public page plus a copy-link button, shown only when the organization is public. See [#748](https://github.com/AvaCodeSolutions/django-email-learning/issues/748).

## [2.9.0] — 2026-07-24

### Added

- **Configurable dashboard sections** — The Dashboard's sections (setup checklist, overview, quick actions) can now be reordered, dropped, or extended via `DASHBOARD.SECTIONS` in settings (or by overriding `Dashboard.get_dashboard_sections()`), defaulting to `[setup_progress, overview, quick_actions]`. Any number of named `custom_component:<name>` slots can be placed anywhere in that order, resolved against `DASHBOARD.CUSTOM_COMPONENTS` using the same `{componentTag, scriptUrl, styleUrl}` shape as `SIDEBAR.CUSTOM_COMPONENT`. The Welcome greeting always renders first and isn't configurable.

### Fixed

- **Dashboard newsletter checklist item and quick action showed up without newsletter-creation access** — Both were gated only on the newsletters feature being viewable, not on whether the organization can actually create a new one. They now require both flags; the newsletter subscriber count on the overview still only depends on the feature being viewable, since that's a separate concern from being able to create a new newsletter.
- **Dashboard overview showed a placeholder message instead of just hiding** — When there are no active courses or newsletter subscribers to show, the Overview section now hides entirely instead of rendering an explanatory placeholder box.
- **Dashboard cards were flush against the screen edges on mobile** — Added small horizontal padding to the outer container on mobile viewports.

## [2.8.1] — 2026-07-24

### Fixed

- **Dashboard 403'd when it was the first page loaded after login** — The Dashboard was gated by a decorator that only reads the session's active organization rather than resolving it, so a session with no active organization seeded yet (the state right after login) failed the check before the view had a chance to seed it. Every other page using that decorator was only ever reached after a page without it had already seeded the session, so the bug only showed up now that Dashboard is the landing page. Dashboard no longer uses that decorator, matching the same pattern the Courses page already used.

## [2.8.0] — 2026-07-24

### Added

- **Platform Dashboard as the new landing page** — Logging in now lands on a new Dashboard page instead of redirecting straight to Courses. It greets the user, shows a setup checklist (create a course, invite your team, complete the organization profile, set up a newsletter) that only lists incomplete steps and disappears once everything's done, and an overview of active courses, enrolled learners, newsletter subscribers, and content delivery health that only shows cards backed by real data.

## [2.7.0] — 2026-07-23

### Added

- **General Info tab on the platform organization page** — The single organization page now has a read-only-by-default "General Info" tab showing the organization's name, description, social links, visibility, and logo, using the same form as the create/edit dialog. An edit icon toggles the form into an editable state; canceling or navigating away discards unsaved changes. The logo now shows as a circular avatar with a placeholder icon and label when none is set, instead of a plain upload button. See [#684](https://github.com/AvaCodeSolutions/django-email-learning/issues/684).

## [2.6.0] — 2026-07-23

### Added

- **"Add to your site" embed-code button for newsletters** — The newsletter detail page now shows an "Add to your site" button (mirroring the course page's) that opens a dialog with a live preview and a ready-to-paste `<script>` tag plus a `<del-newsletter-form>` custom element tag, with color pickers for the subscribe button's background/text color. See [#749](https://github.com/AvaCodeSolutions/django-email-learning/issues/749).

### Fixed

- **Newsletter subscriptions were never confirmed by the subscriber** — Filling out a newsletter subscribe form (public page or embed widget) immediately marked the subscriber as subscribed with no ownership check, so anyone could subscribe an email address they didn't control. Subscribers are now sent a confirmation email and only receive sendouts once they click the confirmation link; the subscribers list and CSV export show each subscriber's confirmation status. Subscriptions created alongside course enrollment (checkbox at signup, or auto-subscribe on verify) are confirmed automatically once the enrollment itself is verified, since that already proves ownership of the email address. See [#751](https://github.com/AvaCodeSolutions/django-email-learning/issues/751).

## [2.5.0] — 2026-07-20

### Added

- **Embed dialog customization: live preview, colors, and optional fields** — The "Add to your site" dialog now shows a live preview of the widget above the code, a color picker for the button's background/text color, and switches to include/exclude the newsletter checkbox, course title, and course image (when the course has one) in the copied snippet.

### Security

- **Fixed XSS in the `del-enroll-form` embed widget** — The widget built its shadow DOM via string-concatenated `innerHTML` with an escaping helper that didn't escape quotes, so a crafted `course_image`, `button_bg_color`, or `button_text_color` attribute value could break out of its HTML attribute and inject a live event handler. Rebuilt the widget's DOM using `createElement`/`textContent`/`setAttribute` (making attribute breakout structurally impossible), and added URL/color format validation as defense in depth. Not exploitable through the platform's own dialog (which already escaped/validated these values), but the widget is a public embeddable contract, so any site author sourcing attribute values from elsewhere (a CMS field, a query param) was exposed.

## [2.4.1] — 2026-07-20

### Fixed

- **AI edit-text input length mismatch and unclear error** — The AI-edit eligibility check allows selections covering multiple top-level blocks (up to 1000 chars of plain text), but the edit-text endpoint's input validation still capped the (markup-included) payload at 500 chars, so a legitimately-eligible multi-block selection could fail with a generic, unhelpful error. Raised the backend limit to 2000 chars to match, and the AI-edit error now shows a specific, actionable message ("try a shorter block" / "try selecting more text") when a selection is still too long or too short, instead of a generic failure message.

## [2.4.0] — 2026-07-20

### Added

- **AI-edit review flow, hint, and expanded block support** — AI-edited text is no longer applied instantly: the AI-edit bubble menu now shows the suggested text for review, with Accept/Reject actions and a note that AI responses can be inaccurate and should be reviewed before accepting. The lesson editor also shows a helper hint near the Save/Back buttons pointing out that a paragraph can be selected for AI rewriting, shown only when AI edit is an allowed feature for the organization. AI-edit eligibility is expanded beyond a single whole paragraph to any selection that exactly covers one or more contiguous top-level blocks (heading, paragraph, bullet list, or blockquote) — e.g. a heading with the paragraph below it, a bullet list, or a heading+list+paragraph group. See [#743](https://github.com/AvaCodeSolutions/django-email-learning/issues/743).

### Fixed

- **Sidebar/navbar not refreshing after switching organizations** — Switching organizations via the dropdown persisted the new active organization to the session but never refreshed the page, so role-gated sidebar/navbar items (parsed once at initial page load) stayed stale until a manual reload even though the user's access had changed. The page now reloads after a successful organization switch. See [#741](https://github.com/AvaCodeSolutions/django-email-learning/issues/741).

## [2.3.0] — 2026-07-20

### Added

- **Embeddable public enroll & newsletter-subscribe API** — Opt-in cross-origin endpoints (`DJANGO_EMAIL_LEARNING["EMBEDDABLE_ENROLLMENT_ENABLED"]`) at `/api/public/embed/<embed_token>/...`, for embedding the enroll/subscribe forms on third-party sites. Each organization gets its own `embed_token` (a publishable identifier, not a secret) instead of a caller-supplied `organization_id`, with independent per-IP/per-email/per-token rate limits (`EMBEDDABLE_ENROLLMENT_RATE_LIMITS`). See [#737](https://github.com/AvaCodeSolutions/django-email-learning/issues/737).
- **"Add to your site" embed-code button** — On the course detail page, public and enabled courses now show an "Add to your site" button that opens a dialog with a ready-to-paste `<script>` tag and a `<del-enroll-form>` custom element tag, letting organizations embed the enrollment form on their own website with no coding required. Automatically includes a newsletter subscribe checkbox when the course has a linked newsletter. See [#738](https://github.com/AvaCodeSolutions/django-email-learning/issues/738).

## [2.2.1] — 2026-07-18

### Added

- **`SocialLink` icons in newsletters** — Added the social links icon to the footer of newsletter email template.

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
