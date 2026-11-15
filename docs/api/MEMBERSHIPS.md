# Memberships and invitations

This guide describes the implemented invited-account workflow. Swagger remains the exact source for request fields, responses, and status codes: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Functional boundary

The invitation is for a person who was already accepted after recruitment outside the public application forms. It does not make the admission decision. Creating it prepares an inactive account, membership, onboarding record, and initial department assignment.

An accepted candidate who already has an active account uses the normal admission workflow and logs in with that account. The invitation API intentionally rejects active existing accounts.

## Create an invitation

`POST /api/v1/memberships/invitations/`

This endpoint requires an access token for a content manager who also has the individual HR permission.

```json
{
  "email": "member@example.com",
  "first_name": "Sara",
  "last_name": "Amrani",
  "department_id": "00000000-0000-0000-0000-000000000000",
  "position_id": "00000000-0000-0000-0000-000000000000"
}
```

The `201` response contains the invitation ID, expiration time, and `setup_token`. The raw token is returned once for testing until email delivery is connected. It must not be logged or stored by the frontend.

Reissuing an invitation for the same inactive invited account cancels the previous token and keeps the same membership. The department and position must remain unchanged during reissue.

## Set up the invited account

`POST /api/v1/memberships/invitations/accept/`

This endpoint is public because the invitation token is the temporary secret. It does not require a login token.

```json
{
  "token": "token-from-the-invitation-message",
  "phone_number": "+212600000000",
  "password": "StrongPassword!2026",
  "password_confirmation": "StrongPassword!2026"
}
```

A `204` response confirms setup. The account becomes active, the unique phone number is stored, the password is set, and the invitation becomes unusable. The member can then log in and continue onboarding.

The server rejects unknown, cancelled, used, or expired tokens, duplicate phone numbers, and passwords that fail validation.

## Security rules

- The token expires after forty-eight hours.
- A user can have only one active membership invitation.
- Only the token's SHA-256 hash is stored.
- An invitation works once.
- Every active account must have a phone number.
- Accepting an invitation never replaces an admission decision.
