# Implemented database schema

Django models and migrations are the source of truth. [AFS_Database.dbml](./AFS_Database.dbml) represents only implemented storage; planned models must not be added early.

## Users

| Column | Purpose |
|---|---|
| ID | Immutable UUID primary key. |
| Email | Required case-insensitive unique login identifier. |
| First name | Required first name. |
| Last name | Required last name. |
| Phone number | Unique contact value; temporarily absent only for an inactive invited account. |
| Password | Django password hash. |
| Active state | Allows or blocks authentication. |
| Staff state | Controls access to Django administration. |
| Superuser state | Grants technical system-wide access. |
| Timestamps | Creation and last-update times. |

A database constraint requires every active account to have a non-empty phone number. Public registration still requires the phone number immediately.

## Departments and positions

A department has a UUID, unique case-insensitive name, description, active state, and timestamps. A position belongs to exactly one department. Position names are unique case-insensitively within a department, while the same name may exist in another department.

Deactivation preserves history. Deleting a referenced department is protected.

## Memberships, onboarding, and assignments

A membership represents the durable relationship between an account and the association. One user can have only one membership. Its initial state waits for onboarding and can later become active or inactive without deleting history.

Each membership has at most one onboarding record. Onboarding belongs to the member and is not recreated during a department transfer.

Admission starts the membership in `pending_onboarding`. Completing onboarding changes it to `active`. A recorded departure closes the current assignment and changes the membership to `inactive` while preserving the account and all history.

An assignment links a membership to one department and one position. It records the assigning user, start date, optional end date, and closure reason. A partial unique PostgreSQL constraint guarantees only one active assignment per membership.

All organization and membership tables, columns, constraints, models, and statuses use English identifiers.

## Membership invitations

An invitation links a membership, invited account, and authorized creator. It stores only the token hash, expiration, and state. A partial unique constraint permits only one active invitation per user. Tokens expire after forty-eight hours, work once, and are invalidated when reissued.

## Events

The `events` table stores title, content, location, event dates, registration window, publication status, QR requirement, creator, and timestamps.

The `event_questions` and `event_question_options` tables define ordered dynamic forms. Supported types are short text, long text, email, phone, single choice, multiple choice, and yes/no.

The `event_registrations` table stores public registrations without creating user accounts. A functional unique constraint on event and lowercase email prevents duplicate registrations case-insensitively. `event_answers` stores one answer per registration and question.

The `event_tickets` table exists only for registrations requiring QR check-in. It stores the QR token hash, delivery status, sent timestamp, and delivery error. The raw token is never stored.

The `event_scanners` table assigns an active membership to one event. `event_check_ins` records the scanner and time. Its one-to-one ticket relationship guarantees one effective check-in per ticket.

## News and gallery content

The `content_page_settings` table stores the editable heading and introduction for the news and gallery pages. One row exists for each section.

The `content_categories` table stores independent, ordered categories for news and gallery. Category names and slugs are case-insensitively unique inside their section. Deactivation hides associated public content while preserving it.

The `news_articles` table stores the title, case-insensitively unique slug, card excerpt, original Markdown body, cover-image path and alternative text, category, publication state and time, featured state, display order, responsible users, and timestamps. Inline article images are represented by URLs inside the Markdown; their bytes are not stored in PostgreSQL.

The `gallery_items` table stores the image path, alternative text, optional caption, category, publication state and time, display order, responsible users, and timestamps.

The singleton `site_settings`, `home_page_content`, `about_page_content`, `get_involved_page_content`, and `events_page_content` tables store typed copy, CTA links, images, accessible alternative text, contact data, and page-specific headings from the approved designs.

The ordered `impact_statistics`, `home_features`, `about_pillars`, `involvement_features`, `donation_options`, and `involvement_steps` tables support repeatable structured sections without creating a free-form page builder. Active state hides an item publicly without deleting it. Impact statistics are shared by Home and About.

The `gallery_videos` table stores validated YouTube URLs with locally managed optional presentation thumbnails, accessible alternative text, duration labels, ordering, and the standard publication lifecycle. Video files are hosted by YouTube and are never uploaded to the application. YouTube video IDs, privacy-enhanced embed URLs, and default thumbnail URLs are derived by the API and are not duplicated in PostgreSQL.

Image files remain outside PostgreSQL. The database stores their relative media paths. Draft and archived records remain available to content managers; public queries return only due published or scheduled records whose category is active.

## Recruitment

The `recruitment_forms` table connects one reusable form to one department and one position. Its ordered questions and choice options use the same seven approved input types as event forms. Form names are case-insensitively unique within their department and position.

The `recruitment_opportunities` table stores public campaign content, an opening window, publication state, and the selected form. Slugs are case-insensitively unique.

The `recruitment_applications` table connects one authenticated applicant to one opportunity and records workflow state, final decision actor and time, and decision-email delivery state. A database constraint permits only one application per applicant and opportunity. `recruitment_answers` stores one immutable JSON value per application question.

The `application_cvs` table stores one CV metadata record per application: private file path, original name, MIME type, size, SHA-256 hash, and upload time. PDF bytes remain outside PostgreSQL and are not exposed through public media URLs.

## Audit records

The `audit_records` table stores immutable recruitment and membership history. Each record contains a domain, approved action, actor, related application or membership, allowlisted previous and new state snapshots, optional reason, and creation time.

At least one business target is required. Recruitment records require an application, and membership records require a membership. Acceptance can reference both so the decision and resulting membership change remain correlated.

Audit state snapshots accept only status, department, position, and assignment identifiers. Passwords, tokens, CV contents, national ID values, and arbitrary request payloads are structurally excluded. Business targets and actors use protected foreign keys so their audit history cannot be removed accidentally.

## Token infrastructure

The JWT library creates active and revoked refresh-token tables through its own migrations. These are authentication infrastructure, not business models.

## Access control

Global roles and permissions use Django's built-in group and permission tables. Access assignments should go through the API or Django administration, not manual DBeaver updates.

## User-model boundary

Memberships, applications, business responsibilities, and national identity numbers do not belong in the user table. They remain in their own domains.
