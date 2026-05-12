# Nexus — personal work dashboard

A lightweight single-page dashboard for fast access to the files, links, and project info I revisit daily across Nokia laptop / personal laptop.

**Stack:** static HTML + JSON, hosted on GitHub Pages. No build step. No dependencies.

## Files
- `index.html` — the dashboard. Reads `data.json` + `notion-projects.json` at load.
- `data.json` — categorized pinned links (SharePoint, OneDrive, Notion, slides, ngCRM, etc.).
- `notion-projects.json` — static snapshot of my Notion project DB. Regenerated on demand.

## Editing
- **Add a link** → edit `data.json`, commit, push, refresh page.
- **Refresh Notion** → I ask Claude on personal laptop to re-export the DB; Claude updates `notion-projects.json` and pushes.
- **Local file paths** → entries with `"local": true` become copy-to-clipboard buttons (browsers block direct `file:///` from an https page).

## Keyboard
- `Ctrl + K` — focus search
- `Esc` — clear search
