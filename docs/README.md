# Project documentation

This file is the single entry point for project documentation. Each subject has one source of truth.

## Find the right document

| Need | Source of truth |
|---|---|
| View available endpoints, required fields, and test the API | [Swagger](http://localhost:8000/api/docs/) |
| Read the raw OpenAPI schema | [OpenAPI schema](http://localhost:8000/api/schema/) |
| Understand tokens and authentication | [Authentication guide](./api/AUTHENTICATION.md) |
| Understand roles and permissions | [Authorization guide](./api/AUTHORIZATION.md) |
| Understand membership lifecycle and invitations | [Membership guide](./api/MEMBERSHIPS.md) |
| Understand events, registrations, and check-in | [Events guide](./api/EVENTS.md) |
| Understand public-page, news, gallery, and media CMS behavior | [Content guide](./api/CONTENT.md) |
| Understand the public donation form and manager submission access | [Donations guide](./api/DONATIONS.md) |
| Understand recruitment forms, applications, CVs, and decisions | [Recruitment guide](./api/RECRUITMENT.md) |
| Understand immutable recruitment and membership audit records | [Audit guide](./api/AUDIT.md) |
| Test authentication manually | [Authentication Postman collection](./api/AFS_Authentication.postman_collection.json) |
| Test roles and permissions manually | [Access-control Postman collection](./api/AFS_Access_Control.postman_collection.json) |
| Test donation submissions manually | [Donations Postman collection](./api/AFS_Donations.postman_collection.json) |
| Understand the V1 functional scope | [Backend V1 scope](./business/BACKEND_SCOPE_V1.md) |
| Understand components and boundaries | [Architecture](./architecture/ARCHITECTURE.md) |
| Find an approved decision | [Decisions](./architecture/DECISIONS.md) |
| Review implemented data storage | [Database schema](./database/SCHEMA.md) |
| Set up, run, or test the project | [Development guide](./development/GUIDE.md) |
| Configure SeaweedFS or migrate existing files | [File storage guide](./development/STORAGE.md) |
| Prepare for production | [Operations](./operations/OPERATIONS.md) |
| Check progress and the next step | [Project progress](../planning/PROJECT_PROGRESS.md) |
| Answer unresolved product questions | [Open questions](../planning/requirements/OPEN_QUESTIONS_V1.md) |
| Review the original specifications | [Functional sources](./business/sources/SOURCES.md) |

## Documentation rules

- Swagger describes only the API that is currently available.
- The functional scope describes all V1 requirements, including features that are not implemented yet.
- The database document describes only implemented tables.
- The progress tracker records status and links to detailed documents.
- Documents link to the source of truth instead of copying it.
