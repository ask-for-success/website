# Events, registrations, and check-in

This guide explains the implemented behavior. Swagger is the exact source for request fields and responses: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Event management

Every user in the `content_manager` group can create and update events. No additional event-management or HR permission is required.

Main endpoints:

- `GET /api/v1/events/`: lists published events publicly; content managers can also see drafts and archived events.
- `POST /api/v1/events/`: creates an event and its registration form.
- `GET /api/v1/events/{event_id}/`: retrieves an event.
- `PATCH /api/v1/events/{event_id}/`: updates an event as a content manager.

Event records also provide an optional cover image with required alternative text and an editable attendance label such as `Free for students`. Use `timing=upcoming` or `timing=past` on the event list. Upcoming events are returned chronologically; past events are returned newest first. The frontend calculates countdown values from `starts_at` rather than storing a countdown in the database.

The form supports `short_text`, `long_text`, `email`, `phone`, `single_choice`, `multiple_choice`, and `yes_no`. Choice questions require at least two options. Question and option display orders must be unique.

The form and the `requires_qr_code` setting cannot be replaced after the first registration. This protects existing answers and tickets from becoming inconsistent.

## Public registration

`POST /api/v1/events/{event_id}/registrations/`

This endpoint is public. It requires an email address and all required form answers, but it never creates a user account.

```json
{
  "email": "visitor@example.com",
  "answers": [
    {
      "question_id": "00000000-0000-0000-0000-000000000000",
      "value": "An answer"
    }
  ]
}
```

An email address can register only once for the same event, regardless of letter case. The same email can register for different events.

Content managers can list registrations with `GET /api/v1/events/{event_id}/registrations/`. Each row contains the submitted answers, QR delivery status, and check-in status.

## Ticket and email delivery

When an event requires QR check-in, the server generates a random code, stores only its hash, and attaches the PNG image to an email sent immediately after registration. An email failure does not delete the registration; the ticket records the `failed` delivery status for later handling.

The local environment uses Django's console email backend by default, so messages and attachments appear in backend logs. Amazon SES is the selected production email provider. The existing `AFS_EMAIL_*` SMTP settings are its configuration boundary, but credentials and live delivery testing are deferred to the final infrastructure phase.

## Event scanners

Any content manager, including a content manager with HR permission, can assign an active member to an event:

- `GET /api/v1/events/{event_id}/scanners/`
- `POST /api/v1/events/{event_id}/scanners/`
- `DELETE /api/v1/events/{event_id}/scanners/{membership_id}/`

```json
{
  "membership_id": "00000000-0000-0000-0000-000000000000"
}
```

This assignment is not a global role. It grants scanner access only for the selected event and can be removed.

## Check-in

`POST /api/v1/events/{event_id}/check-ins/`

```json
{
  "qr_code": "value-read-from-the-qr-code"
}
```

The first valid scan returns `checked_in`. Another scan of the same ticket returns `already_checked_in` without creating a duplicate check-in. Unknown codes and codes belonging to another event are rejected.
