# Implemented database schema

Django models and migrations are the source of truth. [AFS_Database.dbml](./AFS_Database.dbml) represents only implemented storage; planned models must not be added early.

## Users

| Column | Purpose |
|---|---|
| ID | Immutable UUID primary key. |
| Email | Required case-insensitive unique login identifier. |
| First name | Required first name. |
| Last name | Required last name. |
| Phone number | Unique contact value; temporarily absent only for an inactive invited account. |
| Password | Django password hash. |
| Active state | Allows or blocks authentication. |
| Staff state | Controls access to Django administration. |
| Superuser state | Grants technical system-wide access. |
| Timestamps | Creation and last-update times. |

A database constraint requires every active account to have a non-empty phone number. Public registration still requires the phone number immediately.

## Departments and positions

A department has a UUID, unique case-insensitive name, description, active state, and timestamps. A position belongs to exactly one department. Position names are unique case-insensitively within a department, while the same name may exist in another department.

Deactivation preserves history. Deleting a referenced department is protected.

## Memberships, onboarding, and assignments

A membership represents the durable relationship between an account and the association. One user can have only one membership. Its initial state waits for onboarding and can later become active or inactive without deleting history.

Each membership has at most one onboarding record. Onboarding belongs to the member and is not recreated during a department transfer.

An assignment links a membership to one department and one position. It records the assigning user, start date, optional end date, and closure reason. A partial unique PostgreSQL constraint guarantees only one active assignment per membership.

The organization and membership database identifiers are legacy names and are scheduled for the next data-preserving English migration.

## Membership invitations

An invitation links a membership, invited account, and authorized creator. It stores only the token hash, expiration, and state. A partial unique constraint permits only one active invitation per user. Tokens expire after forty-eight hours, work once, and are invalidated when reissued.

## Events

The `events` table stores title, content, location, event dates, registration window, publication status, QR requirement, creator, and timestamps.

The `event_questions` and `event_question_options` tables define ordered dynamic forms. Supported types are short text, long text, email, phone, single choice, multiple choice, and yes/no.

The `event_registrations` table stores public registrations without creating user accounts. A functional unique constraint on event and lowercase email prevents duplicate registrations case-insensitively. `event_answers` stores one answer per registration and question.

The `event_tickets` table exists only for registrations requiring QR check-in. It stores the QR token hash, delivery status, sent timestamp, and delivery error. The raw token is never stored.

The `event_scanners` table assigns an active membership to one event. `event_check_ins` records the scanner and time. Its one-to-one ticket relationship guarantees one effective check-in per ticket.

## Token infrastructure

The JWT library creates active and revoked refresh-token tables through its own migrations. These are authentication infrastructure, not business models.

## Access control

Global roles and permissions use Django's built-in group and permission tables. Access assignments should go through the API or Django administration, not manual DBeaver updates.

## User-model boundary

Memberships, applications, business responsibilities, and national identity numbers do not belong in the user table. They remain in their own domains.
