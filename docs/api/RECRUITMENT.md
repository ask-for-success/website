# Recruitment API guide

Swagger is the executable field-level contract: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/). This guide explains the workflow and permission boundaries that the frontend must preserve.

## Workflow

1. An HR-authorized content manager creates a reusable form for one department and one position.
2. The manager adds ordered questions and activates the form.
3. The manager creates and publishes a recruitment opportunity that uses the form.
4. An authenticated candidate submits the form once with one private PDF CV.
5. HR reviews the candidate row, answers, and protected CV.
6. HR moves the application through review statuses, rejects it, or sends an offer.
7. Sending an offer changes the application to `offer_pending`, records the HR actor and time, and emails the candidate. It does not create membership.
8. The candidate accepts or declines the outstanding offer from their authenticated account.
9. Acceptance records `accepted`, creates or reactivates membership when required, and automatically withdraws the candidate's other non-final applications. Declining records `declined_by_candidate`, creates no membership, and leaves the other applications open.

Multiple applications to different opportunities are allowed until an offer is accepted. Every automatic withdrawal is audited independently.

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
| `PATCH /api/v1/recruitment/applications/{application_id}/status/` | HR review, offer, and rejection transitions. |
| `POST /api/v1/recruitment/applications/{application_id}/offer-response/` | The authenticated applicant accepts or declines an outstanding offer. |
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

Single-choice values are option UUIDs. Multiple-choice values are lists of option UUIDs. Answer records become read-only after submission.

An account can apply only once to the same opportunity. This rule continues after rejection, candidate decline, acceptance, or automatic withdrawal; a final application is never deleted or reopened for reapplication. HR must publish a new opportunity for a later recruitment campaign, and the candidate can apply to that new opportunity with the same account.

## Status and membership behavior

The lifecycle uses `submitted`, `under_review`, `contacted`, `interview`, `offer_pending`, `accepted`, `rejected`, `declined_by_candidate`, and `withdrawn`.

HR can move an application through review, send an offer, or reject it. HR cannot directly set `accepted`, `declined_by_candidate`, or `withdrawn`. Once an offer is outstanding, only its applicant can respond. The response body is:

```json
{
  "response": "accept"
}
```

The other allowed value is `decline`. Repeating a response is rejected because the offer is no longer outstanding.

`offer_pending` sends the offer email. `rejected` sends the rejection email. Candidate acceptance sends an acceptance or onboarding confirmation email. Mail-provider failure is recorded as `failed` but never reverses the corresponding business transition.

Acceptance creates pending membership and the opportunity's department and position assignment for a candidate who has no membership. A former member with completed onboarding is reactivated without repeating onboarding. If a pending or active member accepts an offer for a different assignment, the application becomes accepted but `requires_department_transfer` is true and the existing assignment remains unchanged until HR uses the explicit transfer endpoint.

After acceptance, every other application for that candidate that is not already final becomes `withdrawn`. After a candidate decline, the other applications remain unchanged.

## CV privacy and storage

CVs are not identity documents. The backend accepts only PDF CVs, verifies the file signature, records size and SHA-256 metadata, and stores the file outside PostgreSQL in private storage.

There is no public `/media/` URL for a CV. The API returns a protected download endpoint that checks the applicant or HR permission on every request and sends `private, no-store` caching headers. The current storage backend is local and private. Production will use organization-owned, self-hosted open-source storage, with SeaweedFS planned, but its integration is deferred to the final infrastructure phase.
