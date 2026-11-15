# Approved decisions

This register contains stable project decisions. Other documents should link here instead of repeating the same rules.

## D-001 — Backend framework

The backend uses Django and Django REST Framework.

## D-002 — Database

PostgreSQL is the application database. Django migrations define the real schema.

## D-003 — Local environment

Docker Compose provides Django and PostgreSQL. Additional infrastructure is introduced only when an approved feature requires it.

## D-004 — User identity

Every user has an immutable UUID. Email is the login identifier, but it is not the database identifier.

## D-005 — One account model

Candidates, members, content managers, and administrators share one account model. Business responsibilities remain separate from authentication.

## D-006 — No initial email verification

An active account can log in immediately after registration. Initial email verification is not part of the current design.

## D-007 — Token authentication

Access tokens last fifteen minutes and refresh tokens last seven days. Refresh rotates the pair, logout revokes the submitted refresh token, and password changes invalidate existing sessions.

## D-008 — Project language

English is mandatory for all project artifacts unless the user explicitly requests another language for one specific deliverable.

## D-009 — Interface translation

The frontend translates fixed labels. CMS content currently uses one source language. Multilingual content storage requires a separately approved design.

## D-010 — National identity after admission

The national identity number is requested during onboarding after admission, never during public registration. The system does not accept identity-card scans, images, or files.

## D-011 — Generated OpenAPI contract

OpenAPI, Swagger, and ReDoc are generated from serializers and views. Every new endpoint declares its request, responses, authentication, summary, and description.

## D-012 — Global authorization model

Global roles use Django groups and capabilities use Django permissions. Approved global roles are account administrator and content manager. HR access is an individual permission granted only to selected content managers; it is not a role or account type. Candidate status is contextual, membership belongs to the membership domain, and event scanner access is assigned per event. The user table has no role field.

## D-013 — One active assignment

A member has exactly one active department and position at a time. Multiple applications are allowed, but no decision may create multiple active assignments. Assignment history is retained.

## D-014 — Admission paths

An accepted application creates a membership for the candidate's existing active account. A person recruited outside the application forms receives an invitation created by a content manager with HR permission. The system creates an inactive invited account, membership, onboarding record, and initial assignment. Reissuing the invitation reuses only that inactive invited account.

## D-015 — Applying after departure

When a member leaves, the active assignment ends without deleting the account or history. The person uses the same account for a later application and can receive a new single active assignment.

## D-016 — National identity access

The complete national identity number is visible only to authorized HR content managers and authorized system administrators. Access is sensitive and must be audited. Other users never receive the complete value.

## D-017 — Department transfer

Accepting a current member into another department does not create another membership, active assignment, or onboarding process. An HR-authorized content manager performs an atomic transfer that closes the current assignment and creates the new one. The system records the previous and new departments and positions, actor, timestamp, and required reason.

## D-018 — No multi-department selection screen

The product does not ask a member to select between several accepted departments. Initial admission creates the first assignment. Any later acceptance for an already assigned member uses the explicit transfer operation.

## D-019 — Onboarding happens once

Onboarding belongs to the member, not the department. Message delivery state and onboarding state are separate. Completed onboarding is never repeated after a department transfer, and no email counter determines onboarding status.

## D-020 — Secure invited-account setup

A membership invitation is created only after admission; accepting it never makes a recruitment decision. Its random token expires after forty-eight hours, works once, and is stored only as a hash. Reissuing an invitation immediately cancels the previous active invitation.

The invited account remains inactive with no phone number and an unusable password until setup. The invited person supplies a unique phone number and password, which activates the account without recreating onboarding. Every active account must have a phone number.

## D-021 — Events and check-in

Every content manager can create and update events, build forms, view registrations, and assign scanners. No additional global permission or HR permission is required.

Event registration is public and never creates an account. One email address can register only once per event, case-insensitively. Forms support short text, long text, email, phone, single choice, multiple choice, and yes/no questions.

When QR check-in is enabled, the system creates and emails a secure ticket immediately after registration without manual approval. Only the QR token hash is stored. A content manager can assign any active member as a scanner for one event. The first valid scan records check-in; later scans report that the ticket is already checked in.

## D-022 — News and gallery CMS

Every content manager can manage news, gallery items, their categories, and the editable heading and introduction for each page. No additional CMS or HR permission is required. Public read operations do not require an account.

News and gallery categories are independent. The frontend owns layout and the synthetic **All** filter, while the backend owns content, ordering, visibility, and pagination. Draft and archived content remains private. Scheduled content becomes public when its publication time is reached.

Article bodies use Markdown. The CMS sends the source through `body_markdown`, and PostgreSQL stores that source instead of generated HTML. Inline images are Markdown URLs that refer to files outside PostgreSQL. The public frontend converts Markdown to sanitized HTML, with raw HTML disabled or sanitized and unsafe URL schemes rejected. Production object storage requires separate operational configuration.

## D-023 — Membership activation and departure

Admission creates one durable membership in `pending_onboarding`, one onboarding record, and one current assignment. Starting onboarding does not activate membership. Completing onboarding changes the membership to `active`, and completed onboarding cannot be reopened.

A department transfer atomically ends the current assignment and creates one replacement without repeating onboarding. A departure requires a reason, ends the current assignment, and changes the membership to `inactive` without deleting the account or history. Reactivation requires a later accepted recruitment decision and is not a general membership-management action.

## D-024 — Recruitment applications and private CVs

A reusable recruitment form belongs to one department and one position. An HR-authorized content manager builds its ordered questions, activates it, and publishes an opportunity that uses it. Department, position, and questions lock after the first application so stored answers retain their meaning.

An application requires an authenticated existing account and is unique per account and opportunity. It stores read-only answers and one PDF CV no larger than 10 MB. CV bytes remain outside PostgreSQL and are available only through an authenticated endpoint to the applicant or an HR-authorized content manager. Private CVs never use a public media URL.

Application states are `submitted`, `under_review`, `contacted`, `interview`, `accepted`, and `rejected`. Only accepted and rejected are final, record the decision actor and time, and trigger a decision email. Delivery failure is recorded without reversing the decision.

Acceptance creates pending membership and an initial assignment for a new member. It reactivates the same durable membership without repeating completed onboarding for a former member. A pending or active member requires the explicit transfer workflow instead of direct acceptance.
