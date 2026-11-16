# Architecture

## Current system

```text
Frontend or Postman
        | HTTP and JSON
        v
  Django REST API
     |          |                   |
     | ORM      | S3-compatible API | SMTP with STARTTLS
     v          v                   v
PostgreSQL   SeaweedFS       Amazon SES (production)
```

Docker Compose starts PostgreSQL, SeaweedFS, an idempotent storage-initialization job, and the Django API. SeaweedFS owns public media and private files in separate buckets. Local email uses Django's console provider; production connects to external Amazon SES through SMTP. Redis and Celery are not present.

## Current boundaries

The `accounts` Django application owns the user model and authentication. Each future business domain receives its own Django application only after its models, rules, and permissions are approved.

The `administration` application owns no business tables. It provides a
read-only account-administrator overview by aggregating current values from the
accounts, membership, recruitment, events, content, donations, and audit
domains. Every underlying record remains owned and changed only by its domain.

Public visitors and public event participants do not need an account. All other account types share the same authentication mechanism; business authorization is handled separately.

## Technical sources of truth

- Django models and migrations define data storage.
- Django storage backends and SeaweedFS bucket policies define file-storage boundaries.
- The shared Django email interface defines transactional delivery; environment configuration selects the console or Amazon SES provider.
- The generated OpenAPI schema defines the available HTTP contract.
- Approved decisions are recorded in [DECISIONS.md](./DECISIONS.md).
- Functional source priority is defined in [SOURCES.md](../business/sources/SOURCES.md).
