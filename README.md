# Ask For Success Backend API

This repository contains the Ask For Success backend API built with Django, PostgreSQL, self-hosted SeaweedFS, Amazon SES production email delivery, and Docker.

Start with the [documentation index](./docs/README.md). It identifies the correct source for each subject and prevents the same information from being maintained in multiple places.

## Current handoff

The V1 backend includes authentication, administrator account management,
permissions, organization and membership workflows, recruitment, CMS content,
donations, events, QR check-in, audit history, SeaweedFS storage integration,
email-provider integration, and backup and recovery tooling.

The frontend should treat the generated OpenAPI contract as the source of truth.
Live Amazon SES credentials, production HTTPS, monitoring, secret management,
and the association-controlled off-site backup server remain deployment tasks.

## Start locally

Requirements: Docker Desktop with Docker Compose.

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose run --rm backend python manage.py migrate
```

Local interfaces:

- API: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- ReDoc: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- OpenAPI schema: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

Development email uses the console provider. Invitation links and transactional
messages appear in the backend logs:

```powershell
docker compose logs -f backend
```

## Frontend integration

- Review and test request and response contracts through Swagger.
- Authenticate protected requests with the JWT access token returned by the
  login endpoint.
- Read the current account's roles and permissions from the access API instead
  of inferring them from email addresses or page routes.
- Use the public endpoints for published content, events, opportunities,
  donations, and event registration.
- Use protected administration, CMS, HR, scanner, membership, and audit
  endpoints only when the current account exposes the required access.

See the [development guide](./docs/development/GUIDE.md) for database access and
verification commands. See the [authorization guide](./docs/api/AUTHORIZATION.md)
and [account-management guide](./docs/api/ACCOUNT_MANAGEMENT.md) for initial
administrator setup and dashboard integration.

## Repository map

- `backend/`: Django API, domain applications, migrations, and automated tests.
- `docs/`: API, architecture, database, development, and operations guides.
- `planning/`: progress, approved requirements, and delivery instructions.
- `operations/`: backup and recovery utility.
- `compose.yaml`: local Django, PostgreSQL, and SeaweedFS stack.
- `compose.recovery.yaml`: isolated backup-restore validation stack.

The credentials in local examples are development values only. Never reuse
them outside a local environment, and never commit a populated `.env` file.
