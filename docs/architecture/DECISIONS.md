# Approved decisions

This register contains stable project decisions. Other documents should link here instead of repeating the same rules.

## D-001 — Backend framework

The backend uses Django and Django REST Framework.

## D-002 — Database

PostgreSQL is the application database. Django migrations define the real schema.

## D-003 — Local environment

Docker Compose provides Django and PostgreSQL. Additional infrastructure is introduced only when an approved feature requires it.

## D-004 — User identity

Every user has an immutable UUID. Email is the login identifier, but it is not the database identifier. A user cannot change the login email after account creation.

## D-005 — One account model

Candidates, members, content managers, and administrators share one account model. Business responsibilities remain separate from authentication.

## D-006 — No initial email verification

An active account can log in immediately after registration. Initial email verification is not part of the current design.

## D-007 — Token authentication

Access tokens last fifteen minutes and refresh tokens last seven days. Refresh rotates the pair, logout revokes the submitted refresh token, and password changes invalidate existing sessions.

## D-008 — Project language

English is mandatory for all project artifacts unless the user explicitly requests another language for one specific deliverable.

## D-009 — Interface translation

The frontend translates fixed labels. CMS content currently uses one source language. Multilingual content storage requires a separately approved design.

## D-010 — National identity after admission

The national identity number is requested during onboarding after admission, never during public registration. The system does not accept identity-card scans, images, or files.

## D-011 — Generated OpenAPI contract

OpenAPI, Swagger, and ReDoc are generated from serializers and views. Every new endpoint declares its request, responses, authentication, summary, and description.

## D-012 — Global authorization model

Global roles use Django groups and capabilities use Django permissions. Approved global roles are account administrator and content manager. HR access is an individual permission granted only to selected content managers; it is not a role or account type. Candidate status is contextual, membership belongs to the membership domain, and event scanner access is assigned per event. The user table has no role field.

## D-013 — One active assignment

A member has exactly one active department and position at a time. Multiple applications are allowed, but no decision may create multiple active assignments. Assignment history is retained.

## D-014 — Admission paths

An accepted application creates a membership for the candidate's existing active account. A person recruited outside the application forms receives an invitation created by a content manager with HR permission. The system creates an inactive invited account, membership, onboarding record, and initial assignment. Reissuing the invitation reuses only that inactive invited account.

## D-015 — Applying after departure

When a member leaves, the active assignment ends without deleting the account or history. The person uses the same account for a later application and can receive a new single active assignment.

## D-016 — National identity access

The complete national identity number is visible only to authorized HR content managers and authorized system administrators. Access is sensitive and must be audited. Other users never receive the complete value.

## D-017 — Department transfer

Accepting a current member into another department does not create another membership, active assignment, or onboarding process. An HR-authorized content manager performs an atomic transfer that closes the current assignment and creates the new one. The system records the previous and new departments and positions, actor, timestamp, and required reason.

## D-018 — No multi-department selection screen

The product does not ask a member to select between several accepted departments. Initial admission creates the first assignment. Any later acceptance for an already assigned member uses the explicit transfer operation.

## D-019 — Onboarding happens once

Onboarding belongs to the member, not the department. Message delivery state and onboarding state are separate. Completed onboarding is never repeated after a department transfer, and no email counter determines onboarding status.

## D-020 — Secure invited-account setup

A membership invitation is created only after admission; accepting it never makes a recruitment decision. Its random token expires after forty-eight hours, works once, and is stored only as a hash. Reissuing an invitation immediately cancels the previous active invitation.

The invited account remains inactive with no phone number and an unusable password until setup. The invited person supplies a unique phone number and password, which activates the account without recreating onboarding. Every active account must have a phone number.

## D-021 — Events and check-in

Every content manager can create and update events, build forms, view registrations, and assign scanners. No additional global permission or HR permission is required.

Event registration is public and never creates an account. One email address can register only once per event, case-insensitively. Forms support short text, long text, email, phone, single choice, multiple choice, and yes/no questions.

When QR check-in is enabled, the system creates and emails a signed secure ticket immediately after registration without manual approval. Only the QR token hash is stored; the signature allows the backend to reproduce the same token for a reschedule notification. A content manager can assign any active member as a scanner for one event. The first valid scan records check-in; later scans report that the ticket is already checked in.

## D-022 — News and gallery CMS

Every content manager can manage news, gallery items, their categories, and the editable heading and introduction for each page. No additional CMS or HR permission is required. Public read operations do not require an account.

News and gallery categories are independent. The frontend owns layout and the synthetic **All** filter, while the backend owns content, ordering, visibility, and pagination. Draft and archived content remains private. Scheduled content becomes public when its publication time is reached.

Article bodies use Markdown. The CMS sends the source through `body_markdown`, and PostgreSQL stores that source instead of generated HTML. Inline images are Markdown URLs that refer to files outside PostgreSQL. The public frontend converts Markdown to sanitized HTML, with raw HTML disabled or sanitized and unsafe URL schemes rejected. Production object storage requires separate operational configuration.

## D-023 — Membership activation and departure

Admission creates one durable membership in `pending_onboarding`, one onboarding record, and one current assignment. Starting onboarding does not activate membership. Completing onboarding changes the membership to `active`, and completed onboarding cannot be reopened.

A department transfer atomically ends the current assignment and creates one replacement without repeating onboarding. A departure requires a reason, ends the current assignment, and changes the membership to `inactive` without deleting the account or history. Reactivation requires a later accepted recruitment decision and is not a general membership-management action.

## D-024 — Recruitment applications and private CVs

A reusable recruitment form belongs to one department and one position. An HR-authorized content manager builds its ordered questions, activates it, and publishes an opportunity that uses it. Department, position, and questions lock after the first application so stored answers retain their meaning.

An application requires an authenticated existing account and is unique per account and opportunity. It stores read-only answers and one PDF CV no larger than 10 MB. CV bytes remain outside PostgreSQL and are available only through an authenticated endpoint to the applicant or an HR-authorized content manager. Private CVs never use a public media URL.

Application states are `submitted`, `under_review`, `contacted`, `interview`, `offer_pending`, `accepted`, `rejected`, `declined_by_candidate`, and `withdrawn`. HR sends an offer or rejects an application; only the authenticated applicant can accept or decline an outstanding offer. Delivery failure is recorded without reversing the related business transition.

Candidate acceptance creates pending membership and an initial assignment for a new member. It reactivates the same durable membership without repeating completed onboarding for a former member. A pending or active member accepting a different assignment keeps the current assignment until HR completes the explicit transfer workflow.

## D-025 — Production infrastructure is deferred

Production files remain under the organization's control in an organization-owned, self-hosted open-source storage service. SeaweedFS is the planned service for CMS media, CVs, and other application files. Local development continues to use the existing public media directory and separate private CV directory. SeaweedFS installation, access policy design, file migration, backup, retention, and delivery configuration belong to the final infrastructure phase and must not interrupt current business-logic development.

Amazon SES is the selected production email provider. Development continues to use Django's console or test email backends through the same email interface. SES credentials and live delivery testing are deferred to the final infrastructure phase. Business decisions and delivery states remain implemented now so introducing both production services later does not require changing domain APIs or workflows.

## D-026 — Predefined structured public-page CMS

The CMS follows the approved page designs through typed, predefined models rather than a free-form page builder or unvalidated page JSON. The backend owns editable copy, uploaded images, accessible alternative text, CTA links, ordered items, activation, publication, and validation. The frontend owns layout, styles, icons, responsive rendering, navigation, and countdown calculations.

Shared site contact and footer data has one source of truth. Impact statistics are shared by Home and About. Upcoming and past event sections query the event domain instead of duplicating event records in page content. News and Gallery retain their publication models, while gallery highlight videos have their own publication records.

Gallery highlight videos are hosted exclusively on YouTube. The CMS stores a validated canonical YouTube URL, and the API derives the video ID, privacy-enhanced embed URL, and default YouTube thumbnail URL. No video binary is uploaded to or stored by the application.

The Get Involved page stores editable donation instructions and CTA content. Operational donation submissions remain separate from CMS page content.

## D-027 — Immutable operational audit trail

Sensitive recruitment and membership operations create audit records inside the same database transaction as the business change. A failure to create the audit record therefore rolls back the protected operation instead of leaving unaudited state.

Records contain an approved action, actor, timestamp, related application or membership, allowlisted previous and new state, and an optional reason. They never contain passwords, tokens, CV contents, national ID values, or complete request payloads. Audit records cannot be created, updated, or deleted through the API and are read-only in Django administration.

The global audit log is visible only to users with `accounts.view_audit_log`, which is included in the `account_administrator` role. HR-authorized content managers create audit history through their business operations but do not automatically receive global audit-log access.

## D-028 — Actor-centered cross-domain activity

An account administrator can search accounts by UUID, email, first name, last name, or full name and open the complete recorded timeline for one actor. Search results also identify the actor's global roles, effective permissions, current membership summary, activity count, and last activity time.

Successful authenticated mutations across account management, access control, organization, CMS, events, recruitment, and membership APIs are audited in the same outer database transaction as the request. Failed mutations are not recorded as completed actions. Account registration and successful login are explicitly recorded without credentials or tokens.

Routine read-only browsing is excluded to keep the log operationally useful. Sensitive reads must be explicitly audited when introduced. Request bodies, query parameters, passwords, tokens, CV contents, and national ID values are never copied into general activity records.

## D-029 — Self-service member summary

Every authenticated account can request `GET /api/v1/memberships/me/`. An account without membership receives a successful response with a null membership so the frontend does not need to interpret membership absence as an API error.

The response is scoped only to the current account. It contains membership and onboarding state, a safe current and previous assignment summary, and active current or upcoming event-scanner assignments. Assignment actors, internal transfer or departure reasons, other accounts, HR-only information, and private recruitment records are excluded.

Pending and inactive members may inspect their own membership and onboarding state. Scanner assignments are returned only for an active membership and exclude inactive assignments, ended events, and archived events.

## D-030 — Candidate-confirmed recruitment offers

HR cannot directly accept an application. An HR-authorized content manager sends an offer, which records the HR actor and time, changes the application to `offer_pending`, and sends the offer email without creating membership.

Only the authenticated applicant can respond. Acceptance changes the application to `accepted`, creates or reactivates membership when required, and atomically marks every other non-final application for the same applicant as `withdrawn`. Each automatic withdrawal has its own audit record. Declining changes only the offered application to `declined_by_candidate`, creates no membership, and leaves all other applications open.

For a pending or active member accepting an offer for a different assignment, acceptance records the recruitment outcome but does not replace the current assignment. The API reports `requires_department_transfer`, and HR must use the explicit audited transfer operation.

## D-031 — Recruitment reapplication uses a new opportunity

An account has at most one application for a recruitment opportunity, permanently and regardless of whether that application is open, accepted, rejected, declined, or withdrawn. Final applications are retained as immutable recruitment and audit history; they are not deleted, reset, or reopened to permit reapplication.

A later recruitment campaign is represented by a newly published opportunity. The person reuses the same account and can submit one new application to that new opportunity, including when it uses the same department, position, and reusable form.

## D-032 — Self-service onboarding activates membership

The accepted candidate's login account remains active before onboarding so the person can log in even if the acceptance email was not read. Email is a notification channel, not the only onboarding entry point. The self-service membership summary tells the frontend whether onboarding is required and whether member features may be accessed.

Only the authenticated member completes onboarding. The required V1 submission contains the national ID number and never an identity-card scan, image, or document. Successful validation atomically stores one normalized unique identity record, completes onboarding, and changes membership from `pending_onboarding` to `active`. HR may mark onboarding in progress but cannot complete it for the member.

Ordinary member responses expose only whether a national ID was collected. The complete value is available through a dedicated endpoint only to HR-authorized content managers, global account administrators, and superusers. Submission and every successful complete-value read are audited without placing the number in audit state.

## D-033 — Fixed donation-interest workflow

Donation-interest records are part of V1. The public form has fixed fields for first name, last name, email, phone number, donation type, and details. Donation type is limited to cash or goods. This workflow records an intention to donate and never processes payment information.

The public response does not echo donor contact data. Content managers can list, search, filter, and read the immutable submissions through protected endpoints. CMS content managers may edit the donation section's explanatory content and CTA links, but they cannot change the operational form schema or rewrite submitted donor data.

After the record is stored, the backend attempts an acknowledgement email telling the donor that the information was received and that the team will make contact later. Email delivery state and errors are retained; failure never deletes the business record. Amazon SES remains the selected production provider for the final infrastructure phase.

## D-034 — Event capacity and lifecycle

An event has an optional positive capacity. A null capacity is unlimited. Only active `registered` registrations consume places. Public and manager-created registrations are confirmed immediately, obey the same capacity and duplicate-email rules, and receive the same confirmation email. A manager cannot exceed capacity and must increase it before adding another participant.

Every confirmation email contains a signed self-service cancellation link, including events without QR check-in. A participant may cancel only while more than twenty-four hours remain before the current event start time. Cancellation is blocked at exactly twenty-four hours and throughout the final twenty-four hours. Successful cancellation releases the place immediately.

After registrations exist, schedule changes use the dedicated reschedule operation. Existing registrations and QR codes remain valid, the registration closing time moves with the event, and participant notification defaults to enabled. The notification contains the new schedule, a cancellation link using the new cutoff, and the same QR image when applicable.

Permanent event cancellation changes the event state to `cancelled`, cancels every active registration, and invalidates check-in. Participant notification defaults to enabled and explains that the event will no longer occur. For either lifecycle operation, a content manager may deliberately disable notification. Delivery attempts and failures are stored without reversing the business operation.

The content-manager event dashboard exposes paginated registration search, operational filters, stable ordering, aggregate capacity and attendance statistics, and a CSV export containing readable form answers. Confirmation, reschedule, and cancellation delivery attempts share one filterable notification-history API. These administration endpoints do not grant scanner access and remain restricted to content managers.

## D-035 — Explicit internal member announcements

Important content is not inferred from events, news, dates, or categories. A content manager explicitly creates an internal announcement when information belongs in the member area. An announcement contains a title, message, publication time, optional expiration time, and active state. It may optionally reference one event or one news article, but never both.

Only active members may read the current announcement feed. The feed excludes inactive, future, and expired records. Content managers retain a separate management view containing every state and preserve history by deactivating records instead of deleting them.

Announcements are one-way in V1. They do not support replies and do not trigger email. Email delivery may be considered later as a separate notification decision without changing the stored announcement or member-feed contract.
