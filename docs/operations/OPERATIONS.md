# Operations

The current Docker environment is for local development only. It is not a production deployment.

Before production, the team must approve and implement:

- a production WSGI or ASGI server;
- secure secret management;
- HTTPS;
- PostgreSQL backups and a restore procedure;
- monitoring and structured logging;
- distributed rate limiting;
- continuous integration;
- deployment and rollback procedures.

Progress for this work is recorded only in [PROJECT_PROGRESS.md](../../planning/PROJECT_PROGRESS.md).
