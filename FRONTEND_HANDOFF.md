# AFS frontend handoff

This handoff covers the English-language React frontend on the `frontend` branch. The app uses local records and can be built and reviewed before backend integration.

## Routes

| Route | Page and working interactions |
| --- | --- |
| `/` | Home. The brand and navigation lead to the shared routes. Donate and participation links go to the matching Get Involved sections. All three summit cards open the featured event. |
| `/about` | About. Calls to action open Get Involved or jump directly to donation and partnership sections. |
| `/get-involved` | Get Involved. `#volunteer`, `#partner`, and `#donate` support direct links. Volunteer, partnership, cash or goods donation, and general contact actions open email drafts. |
| `/gallery` | Gallery. Category filters update the nine available photos. Load More is disabled because all current photos are already shown. Both video controls remain unavailable. |
| `/events` | Events. The hero links to `#upcoming-events`, each event card opens its own detail page, and the featured event offers registration by email before the deadline or an inquiry afterward. |
| `/events/:slug` | Event Details. Back to Events and related cards work. Unknown event slugs show a recovery page linking to `/events`. |
| `/news` | News. Featured and article cards open distinct detail pages. Category filters work across the six latest articles. Pagination displays one available page. |
| `/news/:slug` | Article Details. Back to News and available related stories work. Unknown article slugs show a recovery page linking to `/news`. |

The shared Navbar marks the active section on listing and detail routes. The Navbar Donate button and Footer participation links open and focus the corresponding Get Involved section. The logo links return Home. At narrow widths, the navigation scrolls horizontally to keep focused links visible.

## Detail pages and content

- **Events.** [`events.js`](frontend/src/data/events.js) is the source of the eight event records. [Event Details](frontend/src/pages/EventDetails.jsx) uses the URL slug to resolve the record. `/events/morocco-youth-summit-2026` includes a program, speakers, cover, and a map search for the Ain Chok district of Casablanca. The summit countdown and the transition from registration to inquiry use its local event schedule and deadline. Four other event records provide a date and overview. Three archive records provide a date, location, and photo. Additional fields render only when supplied.
- **Articles.** [`articles.js`](frontend/src/data/articles.js) is the source of the seven stories. [Article Details](frontend/src/pages/ArticleDetails.jsx) uses the URL slug to resolve the record. `/news/salmas-story` includes the complete supplied article, including the byline, quote, and captioned image. The other six stories show their supplied previews with a “Full article unavailable” message. Related stories use the supplied selections for Salma's story and same-category matches where available for other stories.
- Keep existing public slugs stable when replacing local data with a service. The listing and detail pages share their records. Add approved content and alt text to that source so both stay consistent.

## Backend and approved destinations checklist

- [ ] **Event registration and seats.** Supply an approved registration URL or an API for event status, deadlines, capacity, submissions, and confirmation. The current actions open email drafts to AFS. The countdown and displayed registration state are derived locally, and seat availability is handled by email.
- [ ] **Volunteer and partner inquiries.** Supply approved forms or endpoints and define who receives and confirms submissions. The current links open subject-specific email drafts.
- [ ] **Cash and goods donations.** Supply an approved secure payment destination for cash and confirm the intake or drop-off process for goods. The current buttons start email inquiries. The goods copy refers to a form, so confirm the intended destination before adding a form or revising that copy.
- [ ] **News and gallery publishing.** Supply complete copy and bylines for the six previews, approved artwork and alt text, both Gallery video destinations, and additional items before enabling further pagination or Load More. Provide stable IDs, categories, media metadata, and pagination if an API replaces the bundled data.
- [ ] **Event content and venue.** Supply missing event schedules, venue or online-meeting destinations, speakers, and artwork from approved records. Provide the summit's exact venue link or pin to replace the district-level map search.
- [ ] **Contact and social links.** Confirm the public contact inbox, supply a public phone number and official TikTok, YouTube, Instagram, and LinkedIn destinations, and confirm whether the contact email should become a form.
- [ ] **Production routing.** Configure the static host to serve `index.html` for frontend routes, including direct links to event and article details. Verify that the public assets resolve at the site's root.

## Verification and known limitations

- Production build and whitespace checks passed. Chromium exercised eight page types at 1440, 1024, 768, 390, and 320px. Desktop and mobile journeys covered both detail templates, navigation, filters, participation links, and invalid slugs. Email checks verified the draft handoffs.
- The existing small white text on lavender in the Footer, Mission, and Stats sections falls below the normal-text contrast target. Manual screen-reader verification remains open.
- The frontend is ready for code review. Full content, approved external destinations, and any server-backed submissions or payment flows depend on the items above.
