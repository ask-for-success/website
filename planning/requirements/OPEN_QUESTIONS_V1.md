# Open V1 Questions

A question remains here only while an answer is required before implementing the related domain. After a decision, remove the question and add the outcome to [DECISIONS.md](../../docs/architecture/DECISIONS.md).

## Accounts and authorization

### Q-001 — Email changes

Can users change their own email address? If yes, must the new address be verified?

## Recruitment and membership

### Q-003 — Non-application membership path

Should V1 still allow a person to submit a direct membership request, or is the only non-application path an invitation started by a content manager with `accounts.manage_hr` after an external interview?

### Q-005 — Reapplication

Can a rejected applicant apply to the same opportunity again? Under which campaign or time rule?

### Q-017 — Invited-account phone number

The current user model requires a unique phone number. For a person invited with only name and email, does the HR-authorized content manager enter the phone number, or does the invitee provide it while setting up the account?

### Q-018 — Other applications after acceptance

When one application is approved and creates the active membership, should the applicant's other pending applications be automatically withdrawn, rejected, or remain open?

### Q-019 — Membership activation point

Should membership use `pending_onboarding` immediately after acceptance and become `active` only after onboarding, or should it be active immediately while member-area access remains separately blocked?

### Q-020 — Administrator scope for national ID

Does national ID access belong to the global `account_administrator`, or will there be a future department-scoped administrator with access only to their department?

## Events

### Q-007 — Capacity with manual approval

Does a pending registration reserve a place, or does only approval consume capacity?

### Q-008 — Duplicate registration

Is a duplicate defined by the same event and email, or by another combination?

### Q-009 — Participant cancellation

Can a participant cancel their registration? Until when, and does capacity reopen immediately?

### Q-010 — Manually added participant

Is a participant added by a manager approved immediately or left pending?

### Q-011 — QR delivery time

Is delivery timing selected freely for each event, or should the system provide a default?

### Q-012 — Event cancellation

What happens to registrations, QR tickets, and notifications when a published event is cancelled?

## Content and operations

### Q-013 — Draft state

Do content and events require an internal draft state before publication?

### Q-014 — Important-content notification

What makes content or an event important enough to create an internal announcement?

### Q-015 — Donations

Are donation-intent records part of V1?

### Q-016 — CMS audit coverage

Must every publication and archive action be audited in V1?
