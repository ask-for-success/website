# Public-page and media CMS

This guide explains the implemented CMS behavior. Swagger is the exact source for request fields and responses: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Access model

Public visitors can read visible site settings, structured pages, categories, news articles, gallery items, and highlight videos without an account. Every user in the `content_manager` group can create and update this content. No additional CMS or HR permission is required.

Content is not permanently deleted through the API. A content manager preserves its history by changing `publication_status` to `archived` or by deactivating an ordered page item.

## CMS boundary

The backend follows the approved layouts with predefined, typed content. It is not a free-form page builder. The backend owns text, images, links, ordering, activation, publication, and validation. The frontend owns spacing, colors, typography, responsive layout, icons, countdown rendering, and navigation behavior.

## Shared site and footer content

- `GET|PATCH /api/v1/content/site/`

This singleton stores the organization name, tagline, contact email, phone, location, and TikTok, YouTube, Instagram, and LinkedIn URLs. Public visitors can read it, while only content managers can change footer contact details or social-media links.

## Structured public pages

The singleton page endpoints are public for reading and restricted to content managers for updates:

- `GET|PATCH /api/v1/content/pages/home/`
- `GET|PATCH /api/v1/content/pages/about/`
- `GET|PATCH /api/v1/content/pages/get-involved/`
- `GET|PATCH /api/v1/content/pages/events/`

Each page exposes named fields matching its approved design. Images use `multipart/form-data` and require alternative text. CTA links accept an internal path or a complete HTTP or HTTPS URL.

The Home response includes active involvement cards and shared impact statistics. The About response includes active pillars and the same shared statistics. The Get Involved response includes active volunteer and partner features, donation-option copy, and process steps.

Ordered content is managed through:

- `GET|POST /api/v1/content/impact-statistics/`
- `GET|PATCH /api/v1/content/impact-statistics/{item_id}/`
- `GET|POST /api/v1/content/home/features/`
- `GET|PATCH /api/v1/content/home/features/{item_id}/`
- `GET|POST /api/v1/content/about/pillars/`
- `GET|PATCH /api/v1/content/about/pillars/{item_id}/`
- `GET|POST /api/v1/content/get-involved/features/`
- `GET|PATCH /api/v1/content/get-involved/features/{item_id}/`
- `GET|POST /api/v1/content/get-involved/donation-options/`
- `GET|PATCH /api/v1/content/get-involved/donation-options/{item_id}/`
- `GET|POST /api/v1/content/get-involved/steps/`
- `GET|PATCH /api/v1/content/get-involved/steps/{item_id}/`

Public lists omit inactive items. Content managers receive active and inactive items. `display_order` controls frontend ordering. Donation options contain editable explanatory content and CTA links. The fixed operational donation form and protected submissions are documented separately in [DONATIONS.md](./DONATIONS.md).

## Editable page text

The headings and introductions shown above the news and gallery grids are CMS content:

- `GET /api/v1/content/pages/news/`
- `PATCH /api/v1/content/pages/news/`
- `GET /api/v1/content/pages/gallery/`
- `PATCH /api/v1/content/pages/gallery/`

The initial values follow the approved design. The `GET` operations are public; the `PATCH` operations require content-manager access.

## Categories

News and gallery categories are independent and ordered. The frontend creates the **All** filter itself; **All** is not stored as a category.

- `GET|POST /api/v1/content/news/categories/`
- `GET|PATCH /api/v1/content/news/categories/{category_id}/`
- `GET|POST /api/v1/content/gallery/categories/`
- `GET|PATCH /api/v1/content/gallery/categories/{category_id}/`

Public requests return active categories only. Content managers also receive inactive categories. Deactivating a category hides its associated content from public responses without deleting it.

The initial news categories are Events, Student stories, Partners, and Announcements. The initial gallery categories are Summits, Workshops, Outreach, Community, and Behind the scenes. Content managers can rename, reorder, deactivate, or add categories.

## News articles

- `GET|POST /api/v1/content/news/`
- `GET|PATCH /api/v1/content/news/{article_slug}/`

An article contains a category, title, URL slug, card excerpt, Markdown body, cover image, accessible cover-image description, publication state, publication time, featured state, and display order.

The CMS editor sends the article content through `body_markdown`. PostgreSQL stores the original Markdown and does not store generated HTML. Inline images use ordinary Markdown URLs:

```markdown
![Volunteers working with students](https://cdn.example.com/news/volunteers.jpg)
```

The image file remains in public object storage; only its URL is embedded in the Markdown. The public frontend converts Markdown to HTML. It must disable raw HTML or sanitize the generated HTML, restrict unsafe URL schemes, and never execute Markdown content directly. This sanitation is mandatory because CMS content must still be treated as untrusted input.

The list supports `category`, `search`, `page`, and `page_size` query parameters. Content managers can also use `status`. Results contain 12 items by default, with a maximum requested page size of 50.

## Gallery items

- `GET|POST /api/v1/content/gallery/`
- `GET|PATCH /api/v1/content/gallery/{item_id}/`

A gallery item contains an image, accessible alternative text, optional visible caption, category, publication state, publication time, and display order. The list supports the same category, search, status, and pagination behavior as news.

## Gallery highlight videos

- `GET|POST /api/v1/content/gallery/videos/`
- `GET|PATCH /api/v1/content/gallery/videos/{video_id}/`

A highlight video is hosted on YouTube and is never uploaded through this API. The CMS stores a validated `youtube_url` together with its title, optional locally managed presentation thumbnail, thumbnail alternative text, duration label, publication state, publication time, and ordering. Only YouTube watch, share, Shorts, live, and embed URLs are accepted.

Public responses include `youtube_video_id`, `youtube_embed_url`, and `youtube_thumbnail_url`. The frontend embeds `youtube_embed_url` in its video player and may use `youtube_thumbnail_url` when no custom presentation thumbnail is needed. The privacy-enhanced embed URL uses the `youtube-nocookie.com` domain.

## Publication behavior

The accepted publication states are:

- `draft`: visible only to content managers.
- `scheduled`: becomes publicly visible when `published_at` is reached.
- `published`: publicly visible when `published_at` is reached; the API sets the current time when this field is omitted during publication.
- `archived`: visible only to content managers.

Public responses also require an active category. A public request for a hidden article or gallery item returns `404`.

## Internal member announcements

Internal announcements are one-way CMS content for active members. Creating an announcement is the content manager's explicit decision that the information is important for the member area; the backend does not infer importance from an event or article.

Content-manager operations:

- `GET|POST /api/v1/content/announcements/`
- `GET|PATCH /api/v1/content/announcements/{announcement_id}/`

The management list supports `state`, `search`, `page`, and `page_size`. The accepted derived states are `active`, `scheduled`, `expired`, and `inactive`. Announcements are preserved rather than deleted; a content manager hides one by setting `is_active` to `false`.

Each announcement has a title, message, publication time, optional expiration time, and active state. It may reference one event or one news article, but never both. References are optional because an announcement may contain standalone operational information.

Active members read the current feed through:

- `GET /api/v1/content/member-announcements/`

The feed returns only active announcements whose publication time has arrived and whose expiration time has not passed. Authentication without an active membership is insufficient. Announcements do not send email in V1, and members cannot reply through this API.

## Image uploads

Create and update requests containing an image use `multipart/form-data`. Each image must be a valid raster image no larger than 10 MB. Alternative text is required so the frontend can provide an accessible experience.

Files are stored in the public SeaweedFS bucket and are readable through the configured public media base URL. PostgreSQL stores only the object path and content metadata. SeaweedFS is self-hosted by the organization; private documents use a different bucket and are never exposed through this public URL. Operational configuration and migration instructions are in the [file storage guide](../development/STORAGE.md).
