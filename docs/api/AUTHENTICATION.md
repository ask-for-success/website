# Authentication Guide

This guide explains authentication behavior for frontend and QA teams. Exact endpoints, request fields, response formats, and HTTP status codes are generated in [Swagger](http://localhost:8000/api/docs/) and are not duplicated here.

## Identity model

All accounts use the same user model. Authentication identifies the person; future roles and permissions will determine what that person can do.

The internal identifier is a stable UUID. Email is the login identifier, but it is neither the primary key nor a foreign key.

## Token lifecycle

- The access token is valid for 15 minutes.
- The refresh token is valid for 7 days.
- Every refresh replaces both tokens and revokes the previous refresh token.
- Logout revokes the submitted refresh token.
- A password change invalidates every existing session.

Protected requests send the access token in this header:

```http
Authorization: Bearer <access_token>
```

In Swagger, click **Authorize** and paste only the access token. Swagger adds the `Bearer` prefix automatically.

## Frontend flow

1. Register or log in the user.
2. Store the token pair using the frontend security strategy.
3. Send the access token with every protected request.
4. When access expires, refresh once and replace both previous tokens.
5. If refresh fails, clear the local session and return to login.
6. On application startup, load the current user with the endpoint shown in Swagger.
7. After successful logout, remove both local tokens.
8. After a password change, require a new login.

## Important rules

- Email verification is not required.
- Email comparison is case-insensitive.
- An inactive account cannot log in.
- Public registration never grants administrative access.
- Users cannot change their email yet.

## Manual testing

The [AFS_Authentication.postman_collection.json](./AFS_Authentication.postman_collection.json) collection runs the complete authentication flow. For individual checks, Swagger is preferred because its contract is generated from the current code.
