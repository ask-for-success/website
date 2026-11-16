# Architecture

## Current system

```text
Frontend or Postman
        | HTTP and JSON
        v
  Django REST API
     |          |
     | ORM      | S3-compatible API
     v          v
PostgreSQL   SeaweedFS
```

Docker Compose starts PostgreSQL, SeaweedFS, an idempotent storage-initialization job, and the Django API. SeaweedFS owns public media and private files in separate buckets. Redis, Celery, and a production email service are not present yet.

## Current boundaries

The `accounts` Django application owns the user model and authentication. Each future business domain receives its own Django application only after its models, rules, and permissions are approved.

Public visitors and public event participants do not need an account. All other account types share the same authentication mechanism; business authorization is handled separately.

## Technical sources of truth

- Django models and migrations define data storage.
- Django storage backends and SeaweedFS bucket policies define file-storage boundaries.
- The generated OpenAPI schema defines the available HTTP contract.
- Approved decisions are recorded in [DECISIONS.md](./DECISIONS.md).
- Functional source priority is defined in [SOURCES.md](../business/sources/SOURCES.md).
