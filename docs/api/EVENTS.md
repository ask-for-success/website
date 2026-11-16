# Events, registrations, and check-in

This guide explains the implemented behavior. Swagger is the exact source for request fields and responses: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Event management

Every user in the `content_manager` group can create and update events. No additional event-management or HR permission is required.

Main endpoints:

- `GET /api/v1/events/`: lists published events publicly; content managers can also see drafts, cancelled events, and archived events.
- `POST /api/v1/events/`: creates an event and its registration form.
- `GET /api/v1/events/{event_id}/`: retrieves an event.
- `PATCH /api/v1/events/{event_id}/`: updates an event as a content manager.
- `POST /api/v1/events/{event_id}/reschedule/`: changes the event schedule safely.
- `POST /api/v1/events/{event_id}/cancel/`: permanently cancels the event.

Event records provide an optional positive `capacity`. A null capacity means unlimited places. The response exposes `active_registration_count`, `seats_remaining`, `is_registration_full`, and `is_registration_open`. Only registrations with the `registered` status consume capacity. Public and manual registration close automatically when no place remains.

Event records also provide an optional cover image with required alternative text and an editable attendance label such as `Free for students`. Use `timing=upcoming` or `timing=past` on the event list. Upcoming events are returned chronologically; past events are returned newest first. The frontend calculates countdown values from `starts_at` rather than storing a countdown in the database.

The form supports `short_text`, `long_text`, `email`, `phone`, `single_choice`, `multiple_choice`, and `yes_no`. Choice questions require at least two options. Question and option display orders must be unique.

The form and the `requires_qr_code` setting cannot be replaced after the first registration. Event dates must then be changed through the reschedule endpoint so participants can be notified consistently.

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

Every successful registration is confirmed immediately. There is no pending approval state. The confirmation email always contains a secure cancellation link. When QR check-in is required, it also contains the QR image.

## Manual participants

`POST /api/v1/events/{event_id}/registrations/manual/`

A content manager can add a participant using the same payload as public registration. The same required-answer, duplicate-email, registration-window, and capacity rules apply. A manual registration cannot exceed capacity; the manager must increase event capacity first. The participant receives the normal confirmation email and cancellation link.

Content managers can list registrations with `GET /api/v1/events/{event_id}/registrations/`. Each row includes its `public` or `manual` source, submitted answers, registration status, confirmation-email state, cancellation state, QR delivery state, and check-in state. The response uses page-number pagination with a default page size of 25 and a maximum of 200.

Dashboard query parameters:

- `search`: case-insensitive email search.
- `status`: `registered` or `cancelled`.
- `source`: `public` or `manual`.
- `qr_delivery_status`: `pending`, `sent`, `failed`, or `not_required`.
- `is_checked_in`: `true` or `false`.
- `ordering`: `registered_at`, `email`, `status`, `source`, `confirmation_email_status`, `qr_delivery_status`, or `checked_in_at`; prefix with `-` for descending order.
- `page` and `page_size`: select the result page.

The same search, filters, and ordering can be exported without pagination from `GET /api/v1/events/{event_id}/registrations/export/`. The UTF-8 CSV includes registration state, delivery and check-in state, and one column for every event-form question. Choice answers are exported as their readable option labels rather than database UUIDs.

`GET /api/v1/events/{event_id}/statistics/` returns capacity, registered, cancelled, checked-in, and remaining-seat counts for the administration dashboard.

## Participant cancellation

`POST /api/v1/events/registrations/cancel/`

```json
{
  "cancellation_token": "token-from-the-confirmation-link"
}
```

This public endpoint uses the signed token from the confirmation email. Cancellation is allowed only while more than 24 hours remain before the current event start time. It is blocked at exactly 24 hours and throughout the final 24 hours. A successful cancellation changes the registration to `cancelled` and immediately releases its place.

The frontend route contained in the email reads the `token` query parameter and submits it as `cancellation_token` to this API endpoint.

## Ticket and email delivery

When an event requires QR check-in, the server creates a signed opaque QR value, stores only its hash, and attaches its PNG image to the confirmation email. The deterministic signature lets the backend reproduce the same valid QR for a reschedule notification without storing the raw value.

An email failure does not delete the registration. The registration records confirmation delivery as `failed`; a QR ticket also records its own failed delivery state for later handling.

The local environment uses Django's console email provider by default, so messages and attachments appear in backend logs. Production uses the integrated Amazon SES SMTP provider without changing this API contract. Credentials remain deployment secrets. Configuration and validation are documented in the [email delivery guide](../operations/EMAIL_DELIVERY.md).

## Rescheduling and permanent cancellation

Reschedule an event with:

```http
POST /api/v1/events/{event_id}/reschedule/
```

```json
{
  "starts_at": "2026-12-10T09:00:00+01:00",
  "ends_at": "2026-12-10T17:00:00+01:00",
  "notify_participants": true
}
```

Existing registrations remain active. The registration closing time moves by the same interval as the event. The default `notify_participants` value is `true`. Each active participant receives the new schedule, a cancellation link calculated from the new start time, and the same QR code when QR check-in is enabled.

Permanently cancel an event with:

```http
POST /api/v1/events/{event_id}/cancel/
```

```json
{
  "notify_participants": true
}
```

Permanent cancellation changes the event to `cancelled`, cancels every active registration, releases all places, and invalidates its registration links and QR check-in. Notification defaults to `true` and tells participants that the event will no longer occur. A content manager may deliberately set `notify_participants` to `false`; the API then records no notification attempts.

Both lifecycle endpoints return `notification_count`, `sent_count`, and `failed_count`. Individual delivery attempts for confirmation, rescheduling, and cancellation are retained for operations and troubleshooting.

Content managers can inspect this history with `GET /api/v1/events/{event_id}/notifications/`. The paginated endpoint supports email search, `notification_type`, `delivery_status`, ordering, and page-size parameters.

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

The first valid scan returns `checked_in`. Another scan of the same ticket returns `already_checked_in` without creating a duplicate check-in. Unknown codes, codes belonging to another event, cancelled registrations, and permanently cancelled events are rejected.
