# Audit API

The audit API exposes immutable actor-centered activity records across the backend. It is read-only and is intended for the operational administration dashboard.

## Authorization

Only an authenticated user with `accounts.view_audit_log` can access audit records. The `account_administrator` role includes this permission. HR permission alone does not grant access to the global audit log.

## Endpoints

- `GET /api/v1/audit/actors/?search={name, email, or UUID}`
- `GET /api/v1/audit/actors/{actor_id}/records/`
- `GET /api/v1/audit/records/`
- `GET /api/v1/audit/records/{record_id}/`

Create, update, and delete operations are not available. The Django administration representation is also read-only.

The actor search response includes the account identity, global roles, effective system permissions, current membership summary when present, audit-record count, and last recorded activity. The actor timeline returns every recorded action performed by that account.

## Filters

The record list accepts:

- `domain`: `accounts`, `access_control`, `organization`, `content`, `events`, `recruitment`, or `membership`;
- `action`: an exact action identifier;
- `actor_id`: the UUID of the user who performed the action;
- `application_id`: a recruitment application UUID;
- `membership_id`: a membership UUID;
- `created_from`: an inclusive ISO 8601 timestamp;
- `created_to`: an inclusive ISO 8601 timestamp;
- `page` and `page_size`, with a maximum page size of 200.

## Recorded operations

The current implementation records:

- account registration and successful login;
- successful authenticated create, update, delete, and action requests across account management, access control, organization, CMS, events, recruitment, and membership APIs;
- every recruitment application status change;
- membership creation and reactivation;
- onboarding status changes;
- national ID submission without recording the number;
- every authorized read of a complete national ID number, without recording the number;
- department and position transfers;
- member departures;
- membership invitation creation and acceptance.

Acceptance records correlate the recruitment application and the membership created or reactivated by the same transaction.

Failed requests are not recorded as completed actions. Ordinary read-only page and list requests are intentionally excluded to prevent routine browsing from overwhelming the operational log. Complete national ID reads are the explicit sensitive-read exception and always create an audit record.

## Stored data

Each record contains its domain, action, actor, target type and identifier, normalized API operation, HTTP method, request path without query parameters, related application or membership when applicable, previous state, new state, optional reason, and timestamp. State snapshots use only approved status, assignment identifiers, and the non-sensitive `national_id_collected` boolean.

Audit records never contain passwords, password hashes, invitation tokens, token hashes, CV files or contents, national ID values, or arbitrary request payloads. Unsupported state fields are rejected by model validation.

The full request and response contract is available in [Swagger](http://localhost:8000/api/docs/) under the **Audit** tag.
