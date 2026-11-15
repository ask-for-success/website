# News and gallery content

This guide explains the implemented CMS behavior. Swagger is the exact source for request fields and responses: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

## Access model

Public visitors can read visible page settings, categories, news articles, and gallery items without an account. Every user in the `content_manager` group can create and update this content. No additional CMS or HR permission is required.

Content is not permanently deleted through the API. A content manager preserves its history by changing `publication_status` to `archived`.

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

The image file remains in media or cloud storage; only its URL is embedded in the Markdown. The public frontend converts Markdown to HTML. It must disable raw HTML or sanitize the generated HTML, restrict unsafe URL schemes, and never execute Markdown content directly. This sanitation is mandatory because CMS content must still be treated as untrusted input.

The list supports `category`, `search`, `page`, and `page_size` query parameters. Content managers can also use `status`. Results contain 12 items by default, with a maximum requested page size of 50.

## Gallery items

- `GET|POST /api/v1/content/gallery/`
- `GET|PATCH /api/v1/content/gallery/{item_id}/`

A gallery item contains an image, accessible alternative text, optional visible caption, category, publication state, publication time, and display order. The list supports the same category, search, status, and pagination behavior as news.

## Publication behavior

The accepted publication states are:

- `draft`: visible only to content managers.
- `scheduled`: becomes publicly visible when `published_at` is reached.
- `published`: publicly visible when `published_at` is reached; the API sets the current time when this field is omitted during publication.
- `archived`: visible only to content managers.

Public responses also require an active category. A public request for a hidden article or gallery item returns `404`.

## Image uploads

Create and update requests containing an image use `multipart/form-data`. Each image must be a valid raster image no larger than 10 MB. Alternative text is required so the frontend can provide an accessible experience.

In local development, files are stored under `backend/media/` and served from `/media/`. PostgreSQL stores only the file path and content metadata. Production object storage and delivery configuration remain a production-infrastructure task.
