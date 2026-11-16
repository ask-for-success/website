# Email delivery

Amazon Simple Email Service (SES) is the production email provider. Django uses the SES SMTP interface so membership, recruitment, event, and donation workflows remain independent of AWS-specific code.

## Provider boundary

| Provider | Purpose | Django backend |
|---|---|---|
| `console` | Local development; messages are printed in backend logs | Console email backend |
| `ses` | Production delivery through Amazon SES SMTP | SMTP email backend |

The default provider is `console`. Selecting `ses` without complete credentials and a valid sender stops Django during configuration with a clear error. Credentials are never stored in project files or printed by the verification command.

## Prepare the SES account

Complete these AWS-side steps in one selected SES Region:

1. Verify the organization's sending domain or sender email identity.
2. Publish the SES-provided DNS records and enable DKIM for the sending domain.
3. Create SES SMTP credentials in that same Region. SES SMTP credentials are different from AWS access keys and are Region-specific.
4. Request production access for that Region. While the account remains in the SES sandbox, recipients must also be verified unless an SES mailbox-simulator address is used.
5. Store the SMTP username and password in the deployment secret manager, never in Git.

## Environment configuration

Configure the deployment environment:

```dotenv
AFS_EMAIL_PROVIDER=ses
AFS_DEFAULT_FROM_EMAIL=no-reply@your-verified-domain.example
AFS_EMAIL_TIMEOUT=10
AFS_SES_REGION=eu-west-3
AFS_SES_SMTP_HOST=
AFS_SES_SMTP_PORT=587
AFS_SES_SMTP_USERNAME=replace-through-secret-management
AFS_SES_SMTP_PASSWORD=replace-through-secret-management
```

When `AFS_SES_SMTP_HOST` is empty, Django derives `email-smtp.<region>.amazonaws.com`. Set it explicitly only when AWS provides a different regional endpoint. The integration permits STARTTLS ports `587` and `2587`; port `587` is the default.

Recreate the backend after changing its environment:

```powershell
docker compose up -d --force-recreate backend
```

## Validate without sending

Open an authenticated provider connection without sending a message:

```powershell
docker compose exec backend python manage.py verify_email_delivery
```

The command reports only the provider, backend, and sender. It never prints the SMTP username or password.

## Send one explicit test

After the connection check succeeds, deliberately send one message:

```powershell
docker compose exec backend python manage.py verify_email_delivery --send-to recipient@example.com
```

In the SES sandbox, the recipient must be a verified identity or an SES mailbox-simulator address. A successful command means SES accepted the message; the team must still inspect delivery, bounce, and complaint results in AWS.

## Application behavior

The same provider configuration serves:

- membership invitation and onboarding messages;
- recruitment offer, rejection, and acceptance messages;
- event confirmation, QR ticket, rescheduling, and cancellation messages;
- donation acknowledgements.

These workflows preserve their business records when delivery fails and retain their existing delivery status where the domain model supports it. Email is currently sent synchronously. Automatic retry, bounce and complaint ingestion, and queue-based delivery are separate production-hardening decisions.

## Production checklist

- keep `AFS_EMAIL_PROVIDER=console` outside the production deployment;
- use a verified sender from the configured SES Region;
- inject SMTP credentials through secret management;
- leave STARTTLS enabled and use port `587` or `2587`;
- request SES production access before sending to unverified recipients;
- run the connection-only verification before the explicit delivery test;
- monitor SES sending quotas, bounces, complaints, and account reputation;
- rotate SMTP credentials and retest delivery after rotation.
