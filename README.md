# Ask For Success website

The official Ask For Success (AFS) frontend, maintained by the IT & Development Department. The app uses React, Vite, React Router, and plain CSS. It runs with bundled content and requires no API credentials or environment file for local development.

## Local setup

Use Node.js 22 and npm. The handoff was verified with Node.js 22.16.0 and npm 10.9.2.

Run these commands from the repository root.

```sh
git switch frontend
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`. Use `npm ci` so the installation follows the lockfile.

## Project structure

```text
frontend/
  index.html           Vite entry page
  public/assets/       Images, icons, and other static artwork
  src/
    App.jsx            Route definitions
    main.jsx           React entry point and stylesheet imports
    components/        Shared layout, navigation, cards, and registration UI
    data/              Local event and article records
    pages/             Listing, landing, and detail pages
    styles/            Design tokens, shared styles, detail styles, and breakpoints
```

## Routes

| Route | Page |
| --- | --- |
| `/` | Home |
| `/about` | About |
| `/get-involved` | Get Involved |
| `/gallery` | Gallery |
| `/events` | Events |
| `/events/:slug` | Event Details |
| `/news` | News |
| `/news/:slug` | Article Details |

Try `/events/morocco-youth-summit-2026` and `/news/salmas-story` to view the complete detail examples. See the [frontend handoff](FRONTEND_HANDOFF.md) for the interaction and integration status.

## Development commands

Run the npm commands from `frontend/`.

| Command | Purpose |
| --- | --- |
| `npm ci` | Install dependencies from the lockfile |
| `npm run dev` | Start the development server with hot reload |
| `npm run build` | Write the production bundle to `frontend/dist/` |
| `npm run preview` | Serve the built bundle locally, normally at `http://localhost:4173` |
| `git diff --check` | Check tracked changes for whitespace errors |

The project currently has no npm lint or test script.

## Production build

From `frontend/`, run `npm run build` followed by `npm run preview` to check the output locally. Serve the contents of `frontend/dist/` at the production site's root. Configure the static host to serve `index.html` for app routes so direct links and refreshes work. Serve existing assets directly and return a 404 for missing asset files. Keep `dist/` and `node_modules/` out of Git.
