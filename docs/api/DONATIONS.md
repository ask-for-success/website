# Donation submissions

Swagger is the executable field-level contract: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/). This guide explains the approved donation workflow and permission boundary.

## Public fixed form

`POST /api/v1/donations/submissions/`

The form structure is fixed. It is not a dynamic form builder and does not process a payment. A visitor submits:

```json
{
  "first_name": "Jane",
  "last_name": "Donor",
  "email": "jane@example.com",
  "phone_number": "+212600000000",
  "donation_type": "cash",
  "details": "I would like to support the next workshop."
}
```

`donation_type` must be `cash` or `goods`. `details` explains the intended cash contribution or the goods being offered.

The public response contains only the submission UUID, selected type, acknowledgement-email status, and creation time. It does not echo the donor's contact information or details.

## Acknowledgement email

After storage, the backend immediately attempts to email the donor. The message confirms that Ask For Success received the submission, thanks the donor, and explains that the team will make contact later.

Email delivery state is `pending`, `sent`, or `failed`. Delivery failure never deletes or rolls back the donation record. Development uses the console provider and production uses the integrated Amazon SES SMTP provider. Configuration and validation are documented in the [email delivery guide](../operations/EMAIL_DELIVERY.md).

## Content-manager access

- `GET /api/v1/donations/management/submissions/`
- `GET /api/v1/donations/management/submissions/{submission_id}/`

Only content managers can read donor names, email addresses, phone numbers, donation details, and email-delivery state. The list supports `donation_type`, `email_status`, `search`, `page`, and `page_size`. Search covers first name, last name, email, and phone number.

Submissions are read-only through the API. Content managers cannot rewrite what a donor originally submitted.

## CMS content and footer

The donation section's headings, instructions, CTA labels, and CTA links remain editable through the Get Involved CMS endpoints documented in [CONTENT.md](./CONTENT.md). The form fields and donation-type choices remain fixed.

Footer contact details and social-media links are publicly readable and content-manager editable through `GET|PATCH /api/v1/content/site/`.

