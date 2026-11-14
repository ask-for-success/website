# Project Progress

**Last updated:** November 14, 2026

This file records work status without copying requirements, models, or API contracts. Functional details are in the [V1 scope](../docs/business/BACKEND_SCOPE_V1.md).

## Current position

- **Completed:** Django, PostgreSQL, Docker, user accounts, and authentication implementation.
- **In review:** global roles, permissions, and frontend authorization contract.
- **Parallel review:** authentication behavior and frontend contract.
- **Requirements clarification:** organization, membership, and onboarding.

## Delivery phases

| Phase | Status | Exit condition |
|---|---|---|
| 1. Foundation | Complete | Local environment, structure, and documentation are operational. |
| 2. Accounts and authentication | In review | Product behavior is approved and the frontend confirms the contract. |
| 3. Roles and permissions | In review | Frontend confirmation of the implemented authorization contract. |
| 4. Organization, membership, and onboarding | Clarifying requirements | Membership lifecycle and member access are validated. |
| 5. Integrated recruitment | Not started | Forms, applications, and decisions are validated. |
| 6. CMS and content | Not started | Publishing and media-library behavior are validated. |
| 7. Events and attendance | Not started | Registration, QR tickets, and check-in are validated. |
| 8. Administration and audit | Not started | Administration and traceability are validated. |
| 9. Production services | Not started | Operational requirements are implemented. |

## Current phase review

- [x] User model and migration.
- [x] Registration and login.
- [x] Complete JWT lifecycle.
- [x] Current-user profile read and update.
- [x] Password change and session revocation.
- [x] Automated tests.
- [x] Validated Swagger, ReDoc, and OpenAPI schema.
- [x] Postman collection.
- [ ] Product-owner approval.
- [ ] Frontend-team confirmation.

## Authorization phase

- [x] Confirm global role boundaries.
- [x] Use Django groups and permissions instead of a role field.
- [x] Define account-administrator and content-manager roles.
- [x] Define HR access as an individual permission for selected content managers.
- [x] Keep membership outside global roles.
- [x] Reserve event check-in for event-specific authorization.
- [x] Add current-user access API.
- [x] Add protected role catalog and assignment APIs.
- [x] Add migration seeding for roles and permissions.
- [x] Add automated permission and schema tests.
- [x] Add frontend-facing authorization documentation.
- [x] Add an access-control Postman collection.
- [x] Product-owner approval of the role matrix.
- [ ] Frontend-team confirmation of the authorization contract.

Organization and membership implementation begins after authorization review.

## Membership clarification

- [x] Confirm one active department and position per member.
- [x] Allow applications to multiple departments before acceptance.
- [x] Preserve account and membership history after leaving.
- [x] Reuse the same account for later applications.
- [x] Allow HR-authorized content managers to start invitations for externally interviewed people.
- [x] Restrict complete national ID access to HR-authorized content managers and the approved administrator scope.
- [ ] Confirm invited-account phone-number collection.
- [ ] Confirm the effect of acceptance on other pending applications.
- [ ] Confirm the membership activation point relative to onboarding.
- [ ] Confirm whether national ID administrator access is global or department-scoped.
- [ ] Confirm whether self-submitted direct membership requests remain in V1.
