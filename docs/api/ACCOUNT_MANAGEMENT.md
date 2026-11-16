# Account management API

Swagger is the executable field-level contract:
[http://localhost:8000/api/docs/](http://localhost:8000/api/docs/). This guide
defines the administration workflow and its security boundaries.

## Authorization

All management endpoints require `accounts.manage_accounts`, which is included
in the `account_administrator` role. A content manager or HR-authorized content
manager does not receive this permission automatically.

The public invitation-acceptance endpoint requires a valid single-use token
instead of an authenticated session.

## Endpoints

- `GET /api/v1/account-management/accounts/`
- `POST /api/v1/account-management/accounts/`
- `GET /api/v1/account-management/accounts/{user_id}/`
- `POST /api/v1/account-management/accounts/{user_id}/deactivate/`
- `POST /api/v1/account-management/accounts/{user_id}/activate/`
- `POST /api/v1/account-management/invitations/accept/`

Role and permission assignment remains available through:

- `GET /api/v1/access/options/`
- `GET /api/v1/access/users/{user_id}/`
- `PUT /api/v1/access/users/{user_id}/`

The global dashboard overview is available through:

- `GET /api/v1/administration/overview/`

## Global administration overview

The overview endpoint is restricted to account administrators and returns one
read-only snapshot containing:

- total, active, and inactive accounts;
- active account-administrator, content-manager, and HR-manager counts;
- membership totals grouped by lifecycle status;
- recruitment-opportunity totals and applications grouped by status;
- upcoming and cancelled events, registrations, cancellations, and check-ins;
- news, gallery-item, and gallery-video totals grouped by publication status;
- current member-announcement totals;
- total and last-thirty-day donation-submission counts;
- the last-thirty-day audit count and ten most recent sanitized audit records.

The response contains no CV data, national ID values, credentials, raw tokens,
donor contact details, event-participant contact details, or private file URLs.
The activity window is fixed at thirty days in V1 so every administration client
displays the same operational definition.

## Creating a content manager

The administrator supplies first name, last name, immutable login email, unique
phone number, and whether HR permission should be granted. The backend creates
an inactive account with the `content_manager` role and optional
`accounts.manage_hr` permission, then emails a single-use setup link valid for
forty-eight hours.

The account cannot authenticate until the invited person sets a valid password.
PostgreSQL stores only the setup-token hash. The raw token is returned in the
creation response only when Django `DEBUG` is enabled.

Email failure is recorded on the invitation and does not delete the inactive
account. Calling the activation endpoint for the inactive account cancels the
previous active invitation and issues a new one.

## Searching and reviewing accounts

The account list is paginated and supports:

- `search`: UUID, email, first name, last name, or phone number;
- `is_active`: active or inactive accounts;
- `role`: an exact managed global role key;
- `page` and `page_size`, with a maximum page size of 200.

Each response includes identity, active state, technical staff state, managed
roles, direct permissions, effective permissions, and timestamps. The separate
audit actor API supplies the account's complete activity timeline and current
membership summary.

## Deactivation

Deactivation requires a written reason and performs one atomic account-security
operation:

- blocks authentication immediately;
- invalidates the existing password;
- revokes every outstanding refresh token;
- removes every group and directly assigned permission;
- removes Django staff access;
- cancels any active account setup invitation;
- records the administrator, reason, previous access, and resulting state.

The account, authored content, membership, applications, and audit history are
never deleted. Deactivation does not silently change membership status. A member
departure remains a separate explicit HR operation.

An administrator cannot deactivate their own account. Superusers cannot be
deactivated or reactivated through this API. An administrator may deactivate
another operational administrator when required for offboarding.

## Reactivation

The activation endpoint requires a reason and sends a new password-setup link.
The account remains inactive until that link is accepted. Roles and permissions
removed during deactivation are not restored automatically; the administrator
must deliberately assign the currently approved access through the access API.

## Audit behavior

The immutable audit trail records account invitation creation and acceptance,
deactivation, reactivation invitations, and every access-assignment change.
Audit state contains only approved booleans for active, staff, administrator,
content-manager, and HR access. Passwords, raw tokens, token hashes, email
contents, and arbitrary request data are never stored in audit state.
