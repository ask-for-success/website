# Membership lifecycle and invitations

This guide describes the implemented membership lifecycle. Swagger remains the exact source for request fields, responses, and status codes: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Access and organization reference data

Membership management requires both the `content_manager` role and the individual `accounts.manage_hr` permission. A technical superuser also passes this check. Ordinary content managers, members, and other authenticated users cannot access HR membership records.

The active departments and their active positions are public reference data used by application forms and selection controls:

- `GET /api/v1/organization/departments/`
- `GET /api/v1/organization/departments/{department_id}/`

## List and inspect memberships

- `GET /api/v1/memberships/`
- `GET /api/v1/memberships/{membership_id}/`

The list supports `status`, `department_id`, `search`, `page`, and `page_size`. It returns 25 records by default and at most 100 when a page size is requested.

The detail response contains the account summary, membership status, onboarding state, current assignment, and completed assignment history. A current assignment is the one assignment without an end time.

## Current account member-area summary

`GET /api/v1/memberships/me/`

This self-service endpoint requires authentication but does not require HR permission. It always describes the current account and never accepts another user's or membership's identifier.

The response contains:

- `membership`, including status, onboarding state, current department and position, and a safe assignment-history summary;
- `onboarding_required`, which tells the frontend to show the mandatory onboarding action after login;
- `can_access_member_features`, which remains false until onboarding is completed and membership is active;
- `active_scanner_assignments`, containing active current or upcoming events where the member may scan QR tickets.

An account without membership receives `200` with `membership: null` and an empty scanner-assignment list. Pending and inactive members can see their own membership and onboarding state, but scanner assignments are returned only while the membership is active. Ended events, archived events, and inactive scanner assignments are excluded.

The self-service representation intentionally excludes the member's account record, complete national ID number, assignment actors, internal transfer and departure reasons, other members, invitation data, HR notes, and private recruitment records. `national_id_collected` reports only whether the required value exists.

## Admit an existing account

`POST /api/v1/memberships/admissions/`

This operation is for an already accepted person who has an active account but no membership. It atomically creates:

- one durable membership in `pending_onboarding`;
- one `not_started` onboarding record;
- one initial department and position assignment.

The account must be active, the department and position must be active, and the position must belong to the selected department. The operation rejects an account that already has a membership.

## Onboarding and activation

`POST /api/v1/memberships/me/onboarding/`

The authenticated accepted member submits:

```json
{
  "national_id_number": "AB123456"
}
```

The value is normalized to uppercase and must contain 4 to 20 letters and digits. No identity-card image, scan, or document is accepted. A national ID number can belong to only one membership.

Successful submission atomically records the protected identity value, sets onboarding timestamps and state to `completed`, and changes membership from `pending_onboarding` to `active`. The login account remains active before onboarding so the candidate can reach this endpoint, but `can_access_member_features` remains false until completion. The complete number is never returned in the self-service response.

Email is only a notification channel. If the candidate does not read the acceptance email, the frontend can still discover `onboarding_required: true` from `GET /api/v1/memberships/me/` after login.

HR may mark the process as started through:

`PATCH /api/v1/memberships/{membership_id}/onboarding/`

The HR transition is:

```text
not_started -> in_progress
```

Only the member's self-service submission can complete onboarding and activate membership. Onboarding cannot start until an invited account has completed account setup, and completed onboarding cannot be reopened.

## Protected national ID access

`GET /api/v1/memberships/{membership_id}/identity/`

The complete number is available only to an HR-authorized content manager, an account administrator, or a superuser. Every successful read creates a dedicated audit record. The number itself is never copied into audit state or ordinary membership responses.

## Department transfer

`POST /api/v1/memberships/{membership_id}/transfers/`

A transfer requires a new active department, a position belonging to that department, and a reason. The transaction closes the current assignment and creates exactly one new current assignment. It never creates another membership or onboarding record.

The response includes the new current assignment and the previous assignment in history with its end time and reason.

## Member departure

`POST /api/v1/memberships/{membership_id}/departures/`

A departure is valid only for an active membership and requires a reason. It closes the current assignment and changes the membership to `inactive`. The account remains active, and the membership, onboarding, and assignment history are preserved.

A later accepted application may reactivate the same durable membership through the recruitment workflow. This endpoint cannot reactivate a former member.

## Functional boundary

The invitation is for a person who was already accepted after recruitment outside the public application forms. It does not make the admission decision. Creating it prepares an inactive account, membership, onboarding record, and initial department assignment.

An accepted candidate who already has an active account uses the normal admission workflow and logs in with that account. The invitation API intentionally rejects active existing accounts.

## Create an invitation

`POST /api/v1/memberships/invitations/`

This endpoint requires an access token for a content manager who also has the individual HR permission.

```json
{
  "email": "member@example.com",
  "first_name": "Sara",
  "last_name": "Amrani",
  "department_id": "00000000-0000-0000-0000-000000000000",
  "position_id": "00000000-0000-0000-0000-000000000000"
}
```

The backend immediately attempts to email a secure account-setup link to the invited address. The link points to `/membership/invitation/setup` on `AFS_PUBLIC_WEB_URL`, contains the one-time token, and expires after forty-eight hours.

The `201` response contains the invitation ID, email, expiration time, `email_delivery_status`, `email_sent_at`, and `email_error`. Delivery state is `pending`, `sent`, or `failed`. A delivery failure never rolls back the inactive account, membership, assignment, or invitation, so HR can see that follow-up is required.

When `DEBUG` is enabled, the response also contains `setup_token` for local Postman and automated testing. The field is completely omitted when `DEBUG` is disabled and must never be expected by a production frontend. The raw token is stored only as a SHA-256 hash in PostgreSQL.

Reissuing an invitation for the same inactive invited account cancels the previous token and keeps the same membership. The department and position must remain unchanged during reissue.

Local development uses Django's console email backend, so the complete message and setup link appear in the backend logs. Amazon SES configuration remains deferred to the final infrastructure phase; it will use the same Django email interface without changing this API contract.

## Set up the invited account

`POST /api/v1/memberships/invitations/accept/`

This endpoint is public because the invitation token is the temporary secret. It does not require a login token.

```json
{
  "token": "token-from-the-invitation-message",
  "phone_number": "+212600000000",
  "password": "StrongPassword!2026",
  "password_confirmation": "StrongPassword!2026"
}
```

A `204` response confirms setup. The account becomes active, the unique phone number is stored, the password is set, and the invitation becomes unusable. The member can then log in and continue onboarding.

The server rejects unknown, cancelled, used, or expired tokens, duplicate phone numbers, and passwords that fail validation.

## Security rules

- The token expires after forty-eight hours.
- A user can have only one active membership invitation.
- Only the token's SHA-256 hash is stored.
- An invitation works once.
- Every active account must have a phone number.
- Accepting an invitation never replaces an admission decision.
