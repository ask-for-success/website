# Development Guide

## Prepare the environment

Copy `.env.example` to `.env` if different local values are needed, then run:

```powershell
docker compose up -d --build
docker compose run --rm backend python manage.py migrate
```

The local API is available at `http://localhost:8000`.

SeaweedFS starts with the stack and serves local public media from `http://localhost:8333/afs-public-media`. Configuration, private-file behavior, and local-file migration are documented in the [file storage guide](./STORAGE.md).

`AFS_PUBLIC_WEB_URL` defines the frontend origin used in secure event-cancellation and membership-invitation setup links sent by email. Its local default is `http://localhost:3000`; production must set it to the public website origin.

## Inspect PostgreSQL with DBeaver

The local database is published only on the Windows loopback interface. Create a PostgreSQL connection in DBeaver with these default development values:

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `5433` |
| Database | `afs` |
| Username | `afs` |
| Password | `afs` |
| SSL | Disabled |

The defaults come from `compose.yaml`. A local `.env` file may override the database name, username, password, or host port. `AFS_DB_HOST_PORT` controls the Windows/DBeaver port; `AFS_DB_PORT` remains the PostgreSQL port used between Docker services.

After connecting, open **Databases -> afs -> Schemas -> public -> Tables**. Django models and migrations remain the schema source of truth; DBeaver is for inspection and querying, not for manually changing the schema.

## Verify the work

```powershell
# Tests for the currently implemented domain
docker compose run --rm backend python manage.py test apps.accounts.tests

# Migration consistency
docker compose run --rm backend python manage.py makemigrations --check --dry-run

# OpenAPI contract validity
docker compose run --rm backend python manage.py spectacular --validate
```

## Feature organization

Models, serializers, views, URLs, and tests remain in the Django application that owns the domain. A new business application is created only after its models, rules, and permissions are approved.

Every endpoint requires `drf-spectacular` metadata, behavior tests, and schema coverage. The complete delivery process is defined in [WORKFLOW.md](../../planning/instructions/WORKFLOW.md).
