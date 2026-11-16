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
- one permanent application per account and opportunity, with later campaigns represented by new opportunities;
- an independent lifecycle for each application;
- simultaneous applications to multiple departments before acceptance;
- HR notes that are never visible to applicants;
- an HR-authored offer followed by an authenticated candidate acceptance or decline;
- the actor and timestamp for every offer and final response;
- recruitment processing by a content manager with `accounts.manage_hr`;
- protected candidate detail, answer, and CV access for authorized HR users.

The confirmed lifecycle is `submitted`, `under_review`, `contacted`, `interview`, `offer_pending`, `accepted`, `rejected`, `declined_by_candidate`, and `withdrawn`. HR can send an offer or reject an application but cannot accept an offer for the candidate. Accepting an outstanding offer creates or reactivates membership when needed and withdraws the candidate's other non-final applications. Declining creates no membership and leaves the other applications open.

## Membership and onboarding

An offer accepted by the candidate creates a membership linked to the applicant's existing account. For a person recruited outside the application forms, a content manager with `accounts.manage_hr` starts an invitation using the person's name and email. The system creates or reuses the account, then sends a secure acceptance/onboarding email.

Each active membership contains one department and one position. A person may have only one active placement at a time, while previous placements remain as history. A former member keeps the same account when applying again.

Acceptance creates the membership record, but member-area access remains blocked until required onboarding is complete. The accepted member logs in with the existing account and submits the national ID number through self-service onboarding. Successful validation activates membership immediately. National ID collection follows decision [D-010](../architecture/DECISIONS.md), and complete-value access follows decision [D-016](../architecture/DECISIONS.md).

## Member area

The member area must provide a profile summary, upcoming events, internal announcements, and events for which the member has check-in permission.

The implemented self-service membership summary is available to the authenticated account before activation so the person can see membership and onboarding state. It exposes explicit onboarding-required and member-access booleans without returning the complete national ID number. Active scanner assignments appear only after membership activation. General upcoming events continue to use the public event API. Internal announcements are explicitly created by content managers and become visible only to active members when their publication time arrives and before any expiration time.

Private messaging, replies to announcements, and automatic management access are outside V1.

## CMS and public content

The CMS manages predefined sections rather than a free-form page builder. It covers shared site and footer settings; structured Home, About, Get Involved, Events, News, and Gallery pages; news, stories, media, events, and featured items. Layout and responsive design remain frontend responsibilities.

Language handling follows decision [D-009](../architecture/DECISIONS.md). Media files remain outside PostgreSQL; the database stores metadata and references. The media library is flat, with no planned albums.

## Donations

V1 includes a fixed public donation-interest form for cash or goods. The form stores donor contact information and donation details without processing a payment. Content managers can read the submitted records through protected APIs, while public responses omit contact data. The donor receives an acknowledgement email confirming receipt and future contact; delivery failure is recorded without deleting the submission.

## Events and attendance

V1 must support:

- public registration without automatic account creation;
- immediate confirmation for public and manager-created registrations;
- automatic capacity closure and case-insensitive duplicate enforcement;
- secure self-service cancellation until twenty-four hours before the event;
- safe rescheduling and permanent cancellation with participant notification;
- a signed opaque QR ticket when check-in is required;
- event-specific check-in permission;
- manager-created participants with the same confirmation workflow;
- attendance stored separately from approval;
- operational metrics and exports.

## Notifications and email

Internal announcements are one-way and do not trigger email in V1. Transactional email supports membership invitations, donation acknowledgements, recruitment decisions, event confirmations, QR delivery, rescheduling, and event cancellation through the configured Django email interface. Amazon SES is integrated as the production SMTP provider, while live credentials remain deployment secrets. Password recovery and automatic delivery retries remain later work. An existing-account acceptance email directs the user to onboarding. A new invited account receives secure account-setup and onboarding instructions. Email failure must never reverse a business decision or delete a stored submission.

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
