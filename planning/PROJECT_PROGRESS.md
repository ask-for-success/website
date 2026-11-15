# Project progress

**Last updated:** November 15, 2026

This file records delivery status without duplicating requirements, database models, or API contracts.

## Current position

- **Completed:** Django, PostgreSQL, Docker, user accounts, authentication, organization models, membership lifecycle, recruitment foundation, event foundation, public event registration, QR tickets, scanner assignments, check-in, and the news and gallery CMS foundation.
- **Under review:** global roles, permissions, authentication behavior, and frontend contracts.
- **In progress:** organization, membership, invitations, onboarding, recruitment frontend validation, CMS frontend validation, and production email delivery.
- **Deferred for team review:** production media storage provider and deployment model.

## Delivery phases

| Phase | Status | Exit condition |
|---|---|---|
| 1. Foundation | Completed | Local environment, structure, and documentation operate correctly. |
| 2. Accounts and authentication | Under review | Product and frontend approve the behavior. |
| 3. Roles and permissions | Under review | Frontend confirms the authorization contract. |
| 4. Organization, membership, and onboarding | In progress | Membership lifecycle, assignments, and member access are validated. |
| 5. Integrated recruitment | In progress | Forms, applications, interviews, and decisions are validated. |
| 6. Content management | In progress | News, editable pages, and media are validated. |
| 7. Events and check-in | In progress | Registration, tickets, delivery, and check-in are production-ready. |
| 8. Administration and audit | Not started | Administration and traceability are validated. |
| 9. Production services | Not started | Operational requirements are complete. |

## Accounts and authentication

- [x] User model and migration.
- [x] Registration and login.
- [x] Complete token lifecycle.
- [x] Current-user profile read and update.
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
- [ ] Add national ID only after its administrator scope and audit contract are approved.

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
- [x] Translate event code, API fields, routes, tables, tests, Swagger, and documentation into English.
- [x] Apply and verify the English event database schema.
- [ ] Configure and validate the production email provider.
- [ ] Confirm the event contract with the frontend team.

## Integrated recruitment

- [x] Connect one reusable form to one department and position.
- [x] Support ordered questions, choice options, and the seven approved question types.
- [x] Require at least one question before form activation.
- [x] Lock form scope and questions after the first application.
- [x] Add draft, published, closed, and archived recruitment opportunities.
- [x] Allow an authenticated account to apply once per opportunity.
- [x] Validate answers and store them as read-only application results.
- [x] Require one PDF CV with a 10 MB limit and signature validation.
- [x] Keep CVs in private storage behind applicant-or-HR API authorization.
- [x] Add the HR application dashboard, filtering, detail, answers, and CV access.
- [x] Add submitted, under-review, contacted, interview, accepted, and rejected states.
- [x] Send email only for accepted and rejected final decisions.
- [x] Preserve final decisions if email delivery fails.
- [x] Create pending membership and assignment after first acceptance.
- [x] Reactivate a former member without repeating completed onboarding.
- [x] Require explicit transfer for a candidate with pending or active membership.
- [x] Add migrations, automated tests, Swagger, and frontend documentation.
- [ ] Decide how one acceptance affects the candidate's other pending applications.
- [ ] Confirm the recruitment contract with the frontend team.
- [ ] Configure and validate the production email provider.

## Content management

- [x] Confirm that every content manager can manage news and gallery content.
- [x] Add editable headings and introductions for the news and gallery pages.
- [x] Add independent, ordered categories for news and gallery.
- [x] Add draft, scheduled, published, and archived publication behavior.
- [x] Add news articles with card excerpts, bodies, cover images, and accessible alternative text.
- [x] Add gallery items with images, captions, accessible alternative text, and ordering.
- [x] Add public category filtering, search, and pagination.
- [x] Add protected content-manager create and update operations.
- [x] Add image validation, local media storage, migrations, tests, and Swagger documentation.
- [x] Confirm Markdown article bodies with inline images referenced by URL.
- [ ] Confirm the API contract and card ordering with the frontend team.
- [ ] Select managed storage or self-hosted SeaweedFS after team review.
- [ ] Configure production storage and media delivery only after that decision.

## File storage TODO

Current development behavior is complete enough for API testing:

- CMS images use the local Django media directory.
- Candidate CVs use a separate private local directory.
- CVs have no public media URL and require applicant-or-HR authorization through the API.
- PostgreSQL stores file paths and metadata, not file bytes.

Production storage remains intentionally unimplemented until the team chooses one deployment model:

- managed object storage; or
- organization-owned, self-hosted SeaweedFS using its S3-compatible interface.

After the decision, the storage implementation must include:

- separate public CMS media and private document access policies;
- persistent production volumes or buckets;
- a Django storage adapter without changing API contracts;
- TLS and reverse-proxy configuration;
- backup, restore, retention, and capacity monitoring;
- migration of existing local files;
- automated authorization and upload tests;
- documented recovery procedures.

Do not install SeaweedFS or integrate a cloud provider before the team approves the deployment model.

## Next engineering task

The recommended next backend implementation is an audit trail for sensitive recruitment and membership actions. It should record the action, previous and new state, actor, timestamp, and related application or membership without storing CV contents, tokens, passwords, or national ID values.

## Next implementation

1. Confirm recruitment, membership, news, gallery, and organization contracts with the frontend team through Swagger and Postman.
2. Decide how acceptance affects the candidate's other pending applications. The current implementation leaves them unchanged.
3. Add audit records for sensitive recruitment and membership actions.
4. Configure the production email provider before external decision and QR testing.
5. Choose managed storage or self-hosted SeaweedFS, then implement the approved production storage plan.
6. Add national ID onboarding only after its administrator scope and audit contract are approved.
