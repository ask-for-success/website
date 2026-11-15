# Backend V1 Functional Scope

This document is the single description of planned V1 backend functionality. Implementation status is recorded in the [project progress tracker](../../planning/PROJECT_PROGRESS.md), not in this document.

## Actors

| Actor | General capability |
|---|---|
| Public visitor | Read published content, events, and opportunities; submit a public event registration. |
| Applicant | Manage only their own applications and direct membership requests. |
| Member | Access the member area after acceptance and onboarding. |
| Content manager | Manage explicitly authorized CMS domains. |
| HR-authorized content manager | Process recruitment and official member records when individually granted HR permission. |
| Check-in agent | Record attendance only for assigned events. |
| Administrator | Manage accounts, groups, permissions, and access assignments. |

## Accounts and authentication

V1 covers registration, login, token refresh, logout, the current-user profile, and password changes. Stable rules are defined by decisions [D-004 through D-007](../architecture/DECISIONS.md). The currently available contract is in [Swagger](http://localhost:8000/api/docs/).

Deferred features: password recovery, email changes, social login, and multi-factor authentication.

## Authorization

The global authorization foundation is defined in the [authorization guide](../api/AUTHORIZATION.md). Future domain endpoints must enforce its capability permissions, while object-specific access—especially event check-in—must remain scoped to the related object.

## Recruitment

V1 must support:

- reusable forms owned by departments;
- one position and department per form;
- ordered questions and validated choices;
- form locking after the first application;
- published recruitment opportunities;
- authenticated, transactional application submission with one private PDF CV and read-only answers;
- an independent lifecycle for each application;
- simultaneous applications to multiple departments before acceptance;
- HR notes that are never visible to applicants;
- the actor and timestamp for every final decision;
- recruitment processing by a content manager with `accounts.manage_hr`;
- protected candidate detail, answer, and CV access for authorized HR users.

The confirmed lifecycle is `submitted`, `under_review`, `contacted`, `interview`, `accepted`, and `rejected`. Only the two final states send a decision email.

## Membership and onboarding

An accepted application creates a membership linked to the applicant's existing account. For a person recruited outside the application forms, a content manager with `accounts.manage_hr` starts an invitation using the person's name and email. The system creates or reuses the account, then sends a secure acceptance/onboarding email.

Each active membership contains one department and one position. A person may have only one active placement at a time, while previous placements remain as history. A former member keeps the same account when applying again.

Acceptance creates the membership record, but member-area access remains blocked until required onboarding is complete. National ID collection follows decision [D-010](../architecture/DECISIONS.md), and complete-value access follows decision [D-016](../architecture/DECISIONS.md).

## Member area

The member area must provide a profile summary, upcoming events, internal announcements, and events for which the member has check-in permission.

Private messaging, replies to announcements, and automatic management access are outside V1.

## CMS and public content

The CMS manages predefined sections rather than a free-form page builder. It covers public pages, news, stories, announcements, media, events, and featured items.

Language handling follows decision [D-009](../architecture/DECISIONS.md). Media files remain outside PostgreSQL; the database stores metadata and references. The media library is flat, with no planned albums.

## Events and attendance

V1 must support:

- public registration without automatic account creation;
- automatic or manual approval;
- capacity and duplicate enforcement;
- an opaque QR ticket for an approved registration;
- event-specific check-in permission;
- manual participant lookup;
- attendance stored separately from approval;
- operational metrics and exports.

## Notifications and email

Internal announcements are one-way. Transactional email will later support password recovery, acceptance and onboarding invitations, final decisions, QR delivery, and delivery retries. An existing-account acceptance email directs the user to onboarding. A new invited account receives secure account-setup and onboarding instructions. Email failure must never reverse a business decision.

## Audit

Sensitive account, permission, recruitment, membership, and check-in actions must be audited. Audit records are read-only and contain neither secrets nor national ID values.

## Confirmed exclusions

- frontend implementation in this repository;
- email verification during registration;
- identity-document uploads;
- private member messaging;
- a free-form page builder;
- offline check-in;
- automatic account creation from public event registration;
- plain-text password storage or display.
