# Recruitment API guide

Swagger is the executable field-level contract: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/). This guide explains the workflow and permission boundaries that the frontend must preserve.

## Workflow

1. An HR-authorized content manager creates a reusable form for one department and one position.
2. The manager adds ordered questions and activates the form.
3. The manager creates and publishes a recruitment opportunity that uses the form.
4. An authenticated candidate submits the form once with one private PDF CV.
5. HR reviews the candidate row, answers, and protected CV.
6. HR moves the application through intermediate statuses.
7. `accepted` or `rejected` records the final actor and time and sends the decision email.

Each application has its own lifecycle. Multiple applications to different opportunities are allowed. What happens to other pending applications after one acceptance remains an open product question.

## Permissions

| Operation | Access |
|---|---|
| List published opportunities and read one published opportunity | Public |
| Submit an application and list own applications | Authenticated candidate |
| View own uploaded CV | The applicant |
| Create or update forms and opportunities | Content manager with `accounts.manage_hr` |
| List, filter, inspect, and decide applications | Content manager with `accounts.manage_hr` |
| View any candidate CV | Content manager with `accounts.manage_hr` |

A general content manager without the HR permission cannot access recruitment records or CVs.

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET/POST /api/v1/recruitment/forms/` | List or create recruitment forms. |
| `GET/PATCH /api/v1/recruitment/forms/{form_id}/` | Read or update a form. |
| `GET/POST /api/v1/recruitment/opportunities/` | Public list or HR creation. |
| `GET/PATCH /api/v1/recruitment/opportunities/{opportunity_slug}/` | Public detail or HR update. |
| `POST /api/v1/recruitment/opportunities/{opportunity_id}/applications/` | Submit answers and a CV. |
| `GET /api/v1/recruitment/applications/me/` | List the authenticated candidate's applications. |
| `GET /api/v1/recruitment/applications/` | HR candidate dashboard. |
| `GET /api/v1/recruitment/applications/{application_id}/` | HR detail with answers and CV reference. |
| `PATCH /api/v1/recruitment/applications/{application_id}/status/` | Change workflow status. |
| `GET /api/v1/recruitment/applications/{application_id}/cv/` | Stream the protected PDF CV. |

The HR application list supports `status`, `opportunity_id`, `department_id`, `position_id`, `search`, `page`, and `page_size` query parameters.

## Form rules

Supported question types are `short_text`, `long_text`, `email`, `phone`, `single_choice`, `multiple_choice`, and `yes_no`. Choice questions require at least two ordered options. An active form requires at least one question.

After the first application, the form's department, position, and questions are locked so historical answers retain their meaning. An opportunity cannot switch forms after it receives an application.

## Application request

The application endpoint uses `multipart/form-data`:

- `cv`: one PDF file, maximum 10 MB;
- `answers`: a JSON list sent as a multipart text field.

Example `answers` value:

```json
[
  {
    "question_id": "a9cc1eb5-068a-469e-845c-9d438c7edfd5",
    "value": "I want to contribute my backend experience."
  },
  {
    "question_id": "4284879e-6de7-4f44-ab4a-b8ee028bbf88",
    "value": true
  }
]
```

Single-choice values are option UUIDs. Multiple-choice values are lists of option UUIDs. Answer records become read-only after submission. A user can apply only once to the same opportunity.

## Status and membership behavior

The lifecycle is `submitted`, `under_review`, `contacted`, `interview`, `accepted`, and `rejected`.

Intermediate states do not send email. `accepted` and `rejected` are immutable final decisions and each sends one decision email. A mail-provider failure is recorded as `failed` but does not reverse the decision.

Acceptance creates a pending membership and the opportunity's department and position assignment for a candidate who has no membership. A former member with completed onboarding is reactivated without repeating onboarding. A current pending or active member cannot be accepted directly; HR must use the explicit department-transfer workflow to preserve the one-department rule.

## CV privacy and storage

CVs are not identity documents. The backend accepts only PDF CVs, verifies the file signature, records size and SHA-256 metadata, and stores the file outside PostgreSQL in private storage.

There is no public `/media/` URL for a CV. The API returns a protected download endpoint that checks the applicant or HR permission on every request and sends `private, no-store` caching headers. The current storage backend is local and private. Production will use organization-owned, self-hosted open-source storage, with SeaweedFS planned, but its integration is deferred to the final infrastructure phase.
