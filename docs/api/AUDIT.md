# Audit API

The audit API exposes immutable records for sensitive recruitment and membership operations. It is read-only and is intended for the operational administration dashboard.

## Authorization

Only an authenticated user with `accounts.view_audit_log` can access audit records. The `account_administrator` role includes this permission. HR permission alone does not grant access to the global audit log.

## Endpoints

- `GET /api/v1/audit/records/`
- `GET /api/v1/audit/records/{record_id}/`

Create, update, and delete operations are not available. The Django administration representation is also read-only.

## Filters

The record list accepts:

- `domain`: `recruitment` or `membership`;
- `action`: an exact action identifier;
- `actor_id`: the UUID of the user who performed the action;
- `application_id`: a recruitment application UUID;
- `membership_id`: a membership UUID;
- `created_from`: an inclusive ISO 8601 timestamp;
- `created_to`: an inclusive ISO 8601 timestamp;
- `page` and `page_size`, with a maximum page size of 200.

## Recorded operations

The current implementation records:

- every recruitment application status change;
- membership creation and reactivation;
- onboarding status changes;
- department and position transfers;
- member departures;
- membership invitation creation and acceptance.

Acceptance records correlate the recruitment application and the membership created or reactivated by the same transaction.

## Stored data

Each record contains its domain, action, actor, related application or membership, previous state, new state, optional reason, and timestamp. State snapshots use only approved status and assignment identifiers.

Audit records never contain passwords, password hashes, invitation tokens, token hashes, CV files or contents, national ID values, or arbitrary request payloads. Unsupported state fields are rejected by model validation.

The full request and response contract is available in [Swagger](http://localhost:8000/api/docs/) under the **Audit** tag.
