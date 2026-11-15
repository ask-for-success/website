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

An approved application creates a membership for the candidate's existing active account. A person recruited outside the application forms receives an invitation created by a content manager with HR permission. The system creates an inactive invited account, membership, onboarding record, and initial assignment. Reissuing the invitation reuses only that inactive invited account.

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
