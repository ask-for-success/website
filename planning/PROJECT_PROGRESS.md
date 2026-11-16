# Project progress

**Last updated:** November 16, 2026

This file records delivery status without duplicating requirements, database models, or API contracts.

## Current position

- **Completed:** Django, PostgreSQL, Docker, user accounts, authentication, organization models, membership lifecycle, recruitment foundation, the complete event registration lifecycle, QR tickets, scanner assignments, check-in, the structured public-page and media CMS foundation, the fixed donation-interest workflow, immutable cross-domain audit records, and self-hosted SeaweedFS integration.
- **Under review:** global roles, permissions, authentication behavior, and frontend contracts.
- **In progress:** organization, membership, invitations, onboarding, recruitment frontend validation, and CMS frontend validation.
- **Deferred to the final infrastructure phase:** Amazon SES credentials and live email validation, plus production storage hardening.

## Delivery phases

| Phase | Status | Exit condition |
|---|---|---|
| 1. Foundation | Completed | Local environment, structure, and documentation operate correctly. |
| 2. Accounts and authentication | Under review | Product and frontend approve the behavior. |
| 3. Roles and permissions | Under review | Frontend confirms the authorization contract. |
| 4. Organization, membership, and onboarding | In progress | Membership lifecycle, assignments, and member access are validated. |
| 5. Integrated recruitment | In progress | Forms, applications, interviews, and decisions are validated. |
| 6. Content management | In progress | News, editable pages, and media are validated. |
| 7. Events and check-in | Under review | Frontend confirms registration, capacity, cancellation, notification, ticket, and check-in contracts. |
| 8. Administration and audit | In progress | Administration and traceability are validated. |
| 9. Production services | In progress | SeaweedFS is integrated; email delivery and production hardening remain. |

## Accounts and authentication

- [x] User model and migration.
- [x] Registration and login.
- [x] Complete token lifecycle.
- [x] Current-user profile read and update.
- [x] Keep the login email immutable after account creation.
- [x] Password change and session revocation.
- [x] Automated tests.
- [x] Swagger, ReDoc, and OpenAPI validation.
- [x] Postman collection.
- [ ] Final product-owner approval.
- [ ] Frontend confirmation.

## Authorization

- [x] Confirm global role boundaries.
- [x] Use Django groups and permissions without a role field on the user.
- [x] Define account-administrator and content-manager roles.
- [x] Define HR access as an individual permission for selected content managers.
- [x] Keep membership outside global roles.
- [x] Keep scanner access specific to each event.
- [x] Add access inspection and assignment APIs.
- [x] Add migrations, tests, documentation, and Postman coverage.
- [x] Obtain product-owner approval for the matrix.
- [ ] Obtain frontend confirmation.

## Organization and membership

- [x] Confirm one active assignment per member.
- [x] Retain account and history after departure.
- [x] Reuse the same account for later applications.
- [x] Keep onboarding unchanged during department transfers.
- [x] Require an authorized HR content manager, reason, and history for transfers.
- [x] Create department and position models.
- [x] Create membership, assignment-history, and onboarding models.
- [x] Create secure invitations for people recruited outside forms.
- [x] Use a single-use invitation token that expires after forty-eight hours and is stored only as a hash.
- [x] Allow a missing phone number only for inactive invited accounts.
- [x] Add invitation creation and acceptance APIs.
- [x] Send the secure invitation setup link through Django email.
- [x] Record invitation email delivery state, sent time, and failure details.
- [x] Omit raw invitation tokens from production API responses.
- [x] Add public active department and position reference APIs.
- [x] Add HR-protected membership list and detail APIs.
- [x] Add admission for an accepted person with an existing active account.
- [x] Add onboarding start and completion APIs.
- [x] Activate membership only after onboarding completion.
- [x] Add atomic department transfer with a required reason and history.
- [x] Add member departure while preserving the account and durable membership.
- [x] Add automated tests and Swagger documentation.
- [x] Translate organization and membership code, APIs, tables, fields, tests, and documentation into English.
- [x] Apply and verify the clean English organization and membership schemas.
- [ ] Confirm the membership API contract with the frontend team.
- [x] Connect recruitment acceptance to existing-membership reactivation.
- [x] Add the authenticated self-service membership summary endpoint.
- [x] Return safe current and previous assignments without HR-only actors or reasons.
- [x] Return only active current or upcoming event-scanner assignments for active members.
- [x] Return a stable null-membership response for authenticated non-members.
- [x] Add candidate-owned onboarding completion with immediate membership activation.
- [x] Collect only the national ID number and reject identity-document uploads by design.
- [x] Keep complete national ID values out of ordinary membership responses and audit state.
- [x] Restrict complete national ID reads to HR-authorized managers, account administrators, and superusers.
- [x] Audit national ID submission and every successful complete-value read.
- [x] Expose stable onboarding-required and member-access booleans for the frontend login flow.

## Events and check-in

- [x] Allow every content manager to create and update events.
- [x] Support the seven approved form-question types.
- [x] Allow public registration without an account.
- [x] Enforce one registration per email address and event.
- [x] Generate a QR ticket when required.
- [x] Send the QR code automatically after registration.
- [x] Separate registration, delivery, and check-in state.
- [x] Allow content managers to assign active members as event scanners.
- [x] Limit scanner access to the assigned event.
- [x] Make the first check-in unique and report later scans.
- [x] Add optional event capacity and close registration automatically when full.
- [x] Count only active registrations against capacity and release a place after cancellation.
- [x] Send every participant a confirmation email with a secure cancellation link.
- [x] Allow self-service cancellation only while more than twenty-four hours remain.
- [x] Allow content managers to add participants without exceeding capacity.
- [x] Add safe rescheduling with default participant notification and the same valid QR code.
- [x] Add permanent event cancellation with default participant notification and registration invalidation.
- [x] Retain per-participant lifecycle notification delivery state and errors.
- [x] Add registration email search and status, source, QR-delivery, and check-in filters.
- [x] Add stable registration ordering and page-number pagination.
- [x] Add capacity, registered, cancelled, checked-in, and remaining-seat statistics.
- [x] Add filtered CSV participant export with readable dynamic-form answers.
- [x] Add paginated confirmation, reschedule, and cancellation notification history.
- [x] Translate event code, API fields, routes, tables, tests, Swagger, and documentation into English.
- [x] Apply and verify the English event database schema.
- [ ] Deferred: configure and validate Amazon SES in the final infrastructure phase.
- [ ] Confirm the event contract with the frontend team.

## Integrated recruitment

- [x] Connect one reusable form to one department and position.
- [x] Support ordered questions, choice options, and the seven approved question types.
- [x] Require at least one question before form activation.
- [x] Lock form scope and questions after the first application.
- [x] Add draft, published, closed, and archived recruitment opportunities.
- [x] Allow an authenticated account to apply once per opportunity.
- [x] Keep the one-application rule permanent after every final status.
- [x] Require a new opportunity for a candidate to apply in a later campaign.
- [x] Validate answers and store them as read-only application results.
- [x] Require one PDF CV with a 10 MB limit and signature validation.
- [x] Keep CVs in private storage behind applicant-or-HR API authorization.
- [x] Add the HR application dashboard, filtering, detail, answers, and CV access.
- [x] Add submitted, under-review, contacted, interview, offer-pending, accepted, rejected, candidate-declined, and withdrawn states.
- [x] Add an HR-authored offer transition without creating membership.
- [x] Add the authenticated candidate offer accept-or-decline endpoint.
- [x] Send offer, rejection, and acceptance/onboarding emails at their corresponding transitions.
- [x] Preserve final decisions if email delivery fails.
- [x] Create pending membership and assignment only after candidate acceptance.
- [x] Reactivate a former member without repeating completed onboarding.
- [x] Require explicit transfer after a pending or active member accepts a different assignment.
- [x] Automatically withdraw and audit the candidate's other non-final applications after acceptance.
- [x] Leave other applications open when the candidate declines an offer.
- [x] Add migrations, automated tests, Swagger, and frontend documentation.
- [ ] Confirm the recruitment contract with the frontend team.
- [ ] Deferred: configure and validate Amazon SES in the final infrastructure phase.

## Content management

- [x] Implement typed shared site and footer settings.
- [x] Implement structured Home, About, Get Involved, and Events page content.
- [x] Seed editable copy from the approved page designs.
- [x] Add ordered Home cards, About pillars, shared impact statistics, involvement features, donation instructions, and process steps.
- [x] Keep layout, responsive design, icons, and countdown calculation in the frontend.
- [x] Confirm that every content manager can manage news and gallery content.
- [x] Add editable headings and introductions for the news and gallery pages.
- [x] Add independent, ordered categories for news and gallery.
- [x] Add draft, scheduled, published, and archived publication behavior.
- [x] Add news articles with card excerpts, bodies, cover images, and accessible alternative text.
- [x] Add gallery items with images, captions, accessible alternative text, and ordering.
- [x] Add public category filtering, search, and pagination.
- [x] Add protected content-manager create and update operations.
- [x] Add image validation, storage abstraction, migrations, tests, and Swagger documentation.
- [x] Confirm Markdown article bodies with inline images referenced by URL.
- [x] Add YouTube-hosted gallery highlight videos with validated embed data, optional presentation thumbnails, and publication states.
- [x] Add event cover images, attendance labels, and upcoming/past filtering.
- [x] Keep donation-section instructions and CTA content editable by content managers.
- [x] Keep footer contact details and social-media links editable by content managers.
- [x] Add explicit one-way internal announcements managed by content managers.
- [x] Restrict the current announcement feed to active members.
- [x] Support scheduled publication, expiration, deactivation, and an optional event-or-article reference.
- [x] Keep announcement email delivery outside V1.
- [ ] Confirm the API contract and card ordering with the frontend team.
- [x] Select organization-owned, self-hosted SeaweedFS for application files.
- [x] Integrate SeaweedFS without changing CMS, event, or recruitment API contracts.

## Donations

- [x] Approve donation-interest records for V1.
- [x] Use a fixed public form instead of a dynamic form builder.
- [x] Require donor name, email, phone, cash-or-goods type, and donation details.
- [x] Store submissions independently from editable CMS content.
- [x] Return only a safe receipt from the public endpoint.
- [x] Restrict complete submission lists and details to content managers.
- [x] Add filtering, search, pagination, migrations, tests, and Swagger documentation.
- [x] Send an immediate donor acknowledgement and preserve the record on email failure.
- [ ] Confirm the donation form and dashboard contract with the frontend team.
- [ ] Deferred: configure and validate Amazon SES in the final infrastructure phase.

## File storage

- [x] Run a pinned SeaweedFS service through Docker Compose.
- [x] Persist object data in a dedicated Docker volume.
- [x] Use separate public-media and private-document buckets.
- [x] Allow anonymous reads only from the public bucket.
- [x] Keep candidate CVs behind applicant-or-HR API authorization.
- [x] Integrate Django through the S3-compatible storage backend without changing API contracts.
- [x] Initialize buckets and policies idempotently during stack startup.
- [x] Provide a non-destructive local-file migration command that preserves object paths.
- [x] Add automated storage-policy, URL, migration, and domain regression tests.
- [x] Document local operation and production requirements.
- [ ] Configure an HTTPS public-media reverse proxy for the production deployment.
- [ ] Replace development credentials with production secret management.
- [ ] Implement off-host backups and validate a full restore.
- [ ] Configure retention, capacity monitoring, and recovery alerts.

The implementation source of truth is the [file storage guide](../docs/development/STORAGE.md).

## Administration and audit

- [x] Add immutable audit records with actor, action, timestamp, target, previous state, new state, and reason.
- [x] Record recruitment application status changes.
- [x] Record membership creation, reactivation, onboarding, transfer, departure, and invitation actions.
- [x] Correlate acceptance decisions with the resulting membership operation.
- [x] Reject secrets, CV contents, national ID values, and arbitrary request fields from state snapshots.
- [x] Restrict the read-only audit API to `accounts.view_audit_log`.
- [x] Add filtering, pagination, Swagger, database documentation, and automated tests.
- [x] Record successful authenticated mutations across accounts, access control, organization, CMS, events, recruitment, and membership APIs.
- [x] Record account registration and successful login without credentials or tokens.
- [x] Exclude failed mutations and routine read-only browsing from completed activity.
- [x] Search actors by UUID, email, first name, last name, or full name.
- [x] Add an actor timeline with roles, permissions, membership summary, activity count, and last activity time.
- [ ] Confirm the audit-list contract with the administration frontend.

## Next engineering task

Prepare the Amazon SES production email configuration while preserving the current Django email interface and development console backend. Live credentials and delivery validation require the production account.

## Next implementation

1. Complete the Amazon SES configuration boundary, production documentation, and provider-independent tests.
2. Finish storage deployment hardening: HTTPS media delivery, secret management, backup and restore, retention, and monitoring.
3. Build backend-owned end-to-end acceptance coverage while the frontend remains in static development.
4. Confirm recruitment, membership, content, member-announcement, donations, events, and organization contracts with the frontend team through Swagger.
5. Update and run the complete Postman acceptance collection last.
