# Authorization Guide

This guide explains the global role and permission design. Exact request fields, responses, and status codes are generated in [Swagger](http://localhost:8000/api/docs/).

## Design

Authorization uses Django groups as global role bundles and Django permissions as capabilities. The `users` table has no role column, so one user can hold multiple global roles without duplicating account data.

| Global role | Capabilities |
|---|---|
| `account_administrator` | Manage accounts and access assignments, read the global audit log, and access explicitly protected member identity records. |
| `content_manager` | Manage website content, events, public forms, donations, and event-specific scanner assignments. |

HR is not a global role or a dedicated account type. `accounts.manage_hr` is an additional permission assigned directly to selected content managers. The API rejects this permission unless the user also has the `content_manager` role.

The following concepts are intentionally not global roles:

- an applicant is an authenticated user acting on their own applications;
- membership comes from the durable membership record;
- event check-in access will be assigned for one event at a time;
- `is_staff` controls Django administration access and is separate from business roles;
- a superuser is reserved for technical bootstrap and emergency administration.

## Available API behavior

- Every authenticated user can read their effective system roles and permissions.
- A user with `accounts.manage_access_assignments` can list assignable roles and additional permissions.
- The same permission allows reading and replacing another user's managed access.
- Replacing managed access preserves unrelated Django groups and permissions.
- A non-superuser cannot change their own access.
- Unknown and duplicate role or permission keys are rejected.
- Account administrators can search accounts, create invited content managers,
  and securely deactivate or reactivate accounts through the account-management
  API.
- Access changes are explicitly audited with the previous and resulting managed
  role and permission state.

The frontend should use the current-access endpoint shown in Swagger instead of inferring authorization from email, staff status, or page location.

The complete administration lifecycle is documented in the
[account management guide](./ACCOUNT_MANAGEMENT.md).

## Initial administrator bootstrap

Create the first superuser from the terminal:

```powershell
docker compose run --rm backend python manage.py createsuperuser
```

The Django superuser is not intended for normal daily administration. It bypasses permission checks, can use Django's technical administration site, and exists to create or recover the first operational administrator.

Log in through the normal authentication API, authorize Swagger or Postman with the returned access token, and assign `account_administrator` to the intended operational administrator. The frontend administration dashboard should then use that regular account and the protected account-management, access, and audit APIs. Later assignments do not require the superuser.

For manual review, import [AFS_Access_Control.postman_collection.json](./AFS_Access_Control.postman_collection.json) and set its `admin_email`, `admin_password`, and `target_user_id` variables.

## Review boundary

Global authorization is implemented and reused by the membership, CMS, event, recruitment, and audit domains. The audit log is read-only and requires `accounts.view_audit_log`. Complete national ID access is restricted to HR-authorized content managers, account administrators, and superusers through the dedicated audited membership endpoint.
