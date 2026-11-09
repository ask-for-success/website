# AFS Database Design

**Project:** Ask For Success public website and member platform

**Selected database:** PostgreSQL

**Status:** corrected V1 model ready for team review

## Decision

PostgreSQL is the selected database engine. The model uses UUID identifiers, time-zone-aware timestamps, explicit relationships, and PostgreSQL data types suited to structured application data.

[`AFS_Database.dbml`](./AFS_Database.dbml) represents the AFS business tables. It intentionally excludes technical tables created automatically by Django.

## Tables managed by Django

Django creates and maintains tables including:

- `django_migrations`;
- `django_content_type`;
- `django_session`;
- `auth_group`;
- `auth_permission`;
- user, group, and permission junction tables.

These tables support migrations, sessions, global groups, and global permissions. Django migrations create them, so they must not be duplicated in the business DBML.

AFS keeps a custom user table because the account contains project-specific fields. Django manages global groups and permissions. Event-specific check-in authorization remains in a dedicated AFS business table.

## Main changes

### Identity and membership

- separated account status from membership status;
- added departments and internal positions;
- added each member's primary department and position;
- added mandatory onboarding;
- protected identity documents through sensitive file references;
- added a reusable file and media library.

### Recruitment

- replaced position questionnaires with one reusable form per department;
- locked a department form after its first application;
- moved question choices into a structured table;
- added date questions;
- added the six confirmed application statuses;
- added private HR notes;
- added direct membership requests;
- tracked decision-email delivery separately from the business decision.

### Events

- added registration opening and closing periods;
- added automatic and manual approval modes;
- added QR configuration and delivery state;
- separated registration approval from physical attendance;
- added unique and auditable check-in records;
- added event-scoped check-in authorization;
- stored QR tokens as hashes;
- reduced the public registration form to the confirmed V1 fields.

### Content and CMS

- replaced separate photo and video storage with a shared media library;
- removed gallery albums and categories that are not required in V1;
- unified news, stories, and public announcements;
- added featured-content selections;
- kept fixed public-page sections;
- removed multilingual translations from V1;
- removed notification read state from V1.

### Audit and security

- replaced the basic activity log with an append-only audit log;
- added actor, target, result, request, and technical metadata;
- added explicit deletion policies to every relationship;
- prohibited secrets in site settings;
- kept file contents outside PostgreSQL.

## Business modules

| Module | Responsibility |
|---|---|
| Identity and organization | accounts, members, departments, positions, and files |
| Recruitment | department forms, opportunities, applications, answers, HR notes, and direct membership |
| Events | events, registrations, QR delivery, check-in, and reminders |
| Content and CMS | public content, gallery, page sections, featured items, and notifications |
| Community engagement | donations, partners, and partnership requests |
| Audit | protected history of important actions |

## Required migration constraints

Some PostgreSQL constraints are more specific than portable DBML syntax. Migrations must explicitly add:

- the `citext` extension;
- one active check-in assignment per user and event;
- valid event start, end, registration opening, and registration closing timestamps;
- non-negative capacity, price, donation amount, and file size values;
- exactly one target for each featured item;
- exactly one answer value matching the question type;
- conditional donation fields based on donation type;
- consistency between QR activation and event registration availability.

Department, position, and questionnaire consistency is already enforced through composite foreign keys in the DBML.

## Deletion policy

- user accounts are disabled instead of physically deleted;
- applications, registrations, decisions, check-ins, and audit records are retained;
- public content is archived;
- sensitive file content is removed from object storage according to the retention policy, then its metadata is archived;
- historical relationships use `RESTRICT` to prevent accidental deletion;
- only true dependent records use `CASCADE`.

## Expected result

This model is the source of truth for database migrations. ORM models must preserve the approved names, constraints, relationships, and module responsibilities.
