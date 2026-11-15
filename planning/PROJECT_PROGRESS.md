# Project progress

**Last updated:** November 14, 2026

This file records delivery status without duplicating requirements, database models, or API contracts.

## Current position

- **Completed:** Django, PostgreSQL, Docker, user accounts, authentication, event foundation, public event registration, QR tickets, scanner assignments, and check-in.
- **Under review:** global roles, permissions, authentication behavior, and frontend contracts.
- **In progress:** organization, membership, invitations, onboarding, and production email delivery.

## Delivery phases

| Phase | Status | Exit condition |
|---|---|---|
| 1. Foundation | Completed | Local environment, structure, and documentation operate correctly. |
| 2. Accounts and authentication | Under review | Product and frontend approve the behavior. |
| 3. Roles and permissions | Under review | Frontend confirms the authorization contract. |
| 4. Organization, membership, and onboarding | In progress | Membership lifecycle, assignments, and member access are validated. |
| 5. Integrated recruitment | Not started | Forms, applications, interviews, and decisions are validated. |
| 6. Content management | Not started | News, editable pages, and media are validated. |
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
- [x] Add automated tests and Swagger documentation.
- [ ] Translate the remaining legacy organization and membership implementation into English.
- [ ] Add the remaining membership APIs and frontend contract.

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

## Next implementation

1. Translate the older organization and membership modules into English without losing data.
2. Build the news CMS with draft, published, and archived states.
3. Define editable page sections before implementing page-content APIs.
4. Configure the production email provider before external QR testing.
