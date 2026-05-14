# Nexus — personal Nokia work dashboard

Single-page dashboard for fast access to files, links, projects, products, and personal notes across Nokia / personal laptop. Set as Edge homepage on the Nokia laptop.

**Stack:** static HTML + JSON, GitHub Pages. Nokia Pure web fonts, official 2026 palette. No build step. One CDN dep (`marked.js` for Insights reader). Notion as data backend for Projects + Insights.

---

## Tabs

| # | Tab | Type | Source |
|---|---|---|---|
| 1 | 🏠 **Homepage** | `blocks` (2-col) | `data.json` — 4 blocks (Admin / SE Tools / Design Tools / Competitive Landscape) |
| 2 | 📚 **Products Wiki** | `documents` | `notion-documents.json` (Document Vault) + curated GX / PSS in `data.json` + `📌 My Pins` view (localStorage) |
| 3 | 💡 **Insights** | `insights` | Notion "My Insights" DB → `notion-posts.json` + `posts/*.md` (auto-sync) |
| 4 | 📁 **My Docs** | `docs` | localStorage only — personal scratch-pad on Nokia laptop |
| 5 | 📋 **Projects** | `notion` | Notion "MY PROJECTS" DB → `notion-projects.json` (auto-sync) |

---

## Files

```
nexus/
├── index.html                       Dashboard
├── data.json                        Tab config + Homepage blocks + Products curated subpages
├── notion-projects.json             Auto-synced from Notion Projects DB
├── notion-posts.json                Auto-synced from Notion My Insights DB (index)
├── notion-documents.json            Document Vault snapshot (manually built locally)
├── posts/                           Auto-managed markdown bodies for Insights posts
│   └── *.md
├── assets/
│   └── nokia-logo.svg               Official Nokia Bright Blue wordmark
├── fonts/                           Nokia Pure web fonts (woff2)
│   ├── NokiaPureHeadline_Bd.woff2
│   ├── NokiaPureHeadline_Rg.woff2
│   ├── NokiaPureText_Bd.woff2
│   ├── NokiaPureText_Md.woff2
│   └── NokiaPureText_Rg.woff2
├── scripts/
│   ├── fetch-notion.py              Projects sync (NOTION_TOKEN required)
│   ├── fetch-insights.py            Insights sync (NOTION_TOKEN required)
│   ├── excel-to-docs.py             Document Vault generator (local, manual run)
│   └── manual-docs.json             Hand-curated overlay for excel-to-docs
└── .github/workflows/
    └── notion-sync.yml              Daily 08:00 ICT cron: fetch-notion + fetch-insights
```

---

## Editing flows

### Add/change a Homepage tile or column
Edit `data.json` → commit → push → refresh page (~30s for GitHub Pages).

### Add a Curated subpage entry (GX / PSS)
Edit `data.json` → `tabs[id=products].curatedPages.<gx|pss>.blocks[*].links` → commit → push.

### Pin to "My Pins" or "My Docs" (drag-drop, no GitHub)
- Products Wiki → dropdown **📌 My Pins** view: prototyping/scratch space. Saved in browser localStorage key `nexus.pins`.
- 📁 **My Docs** tab: same UX, separate store (`nexus.docs`). Use this for **local files** (Word/Excel/PPT/folder/.bat) you work with daily.
- Drag a tab from Edge onto a block to pin a URL.
- Use **+ Add link** form for local paths: paste `C:\path\file.xlsx` (right-click in Explorer → Copy as path). Click a local pin → path copied to clipboard, then paste in Explorer's address bar.
- **Export** button downloads JSON backup; **Import** restores.
- Data lives in browser only — wipe browser cache = wipe pins. Backup periodically.

### Publish a new Insight post
1. Notion → "My Insights" DB → `+ New` → fill Title, Summary, Tags, Date, Important
2. Write body in the Notion page (rich text — supports headings, lists, tables, code, callouts)
3. Set **Status = Published**
4. Sync runs auto at 08:00 ICT daily. To run now: GitHub → **Actions** → `Sync Notion (projects + insights)` → **Run workflow**.
5. Refresh dashboard → new card appears in 💡 Insights → click to read inline.

### Refresh Projects
- Auto: daily 08:00 ICT
- On demand: GitHub → Actions → **Run workflow**

### Refresh Products Wiki (Document Vault) from OneStore xlsx
Done **locally on personal laptop** — GitHub Actions does NOT run this:
```
python scripts/excel-to-docs.py \
  --xlsx path/to/onestore-export.xlsx \
  --extras scripts/manual-docs.json \
  --out notion-documents.json
```
Commit + push `notion-documents.json`.

---

## Branding

- **Logo**: `assets/nokia-logo.svg` — official Nokia 2023 wordmark (Bright Blue `#005AFF`).
- **Fonts**: Nokia Pure Text (body) + Nokia Pure Headline (titles). woff2 hosted in `fonts/`.
- **Palette** (official 2026 from PPT toolkit):
  - `#005AFF` Bright Blue (primary accent)
  - `#001135` Dark Navy (text, headings)
  - `#666666` Grey (muted text)
  - `#EBEBEB` Light Grey (borders)
  - `#23ABB6` Teal · `#37CC73` Green · `#F47F31` Orange · `#E03DCD` Pink · `#7D33F2` Purple

---

## Secrets

- `NOTION_TOKEN` (GitHub repo secret) — Notion integration token. Integration name in Notion: `nexus-auto-sync`. **Never hardcode** — Notion auto-revokes leaked tokens.
- Both Notion DBs (`MY PROJECTS`, `My Insights`) must be shared with `nexus-auto-sync` via **Connections**.

---

## Keyboard shortcuts

- `Ctrl + K` — focus search (filters visible tab content)
- `Esc` — clear search
- `1` / `2` / `3` / `4` / `5` — switch main tab

---

## Two-laptop constraint

| | Nokia laptop | Personal laptop |
|---|---|---|
| Access dashboard (read-only) | ✅ Edge homepage | ✅ |
| Edit Notion (Projects / Insights) | ✅ when network allows | ✅ |
| Edit code, run scripts, push to GitHub | ❌ | ✅ via Cowork |
| Pins / Docs (localStorage) | ✅ saved here | ✅ separate copy |

My Pins / My Docs do **not** sync between laptops — by design. Use Export/Import JSON for backup or 1-off migration.

---

## Versions

- v3.5 (2026-05-14) — Nokia Pure fonts + official Bright Blue logo + 2026 palette; My Docs tab added; sync buttons moved to tab footer
- v3.4 — Insights tab wired to Notion DB; sync action moved to footer
- v3.3 — Insights tab (mock data) with inline markdown reader
- v3.2 — My Pins multi-page + local file pinning
- v3.1 — Homepage `type: blocks` (4-block 2-col); curated GX/PSS subpages
- v3.0 — Notion-driven Products Wiki via Document Vault
- v2.x — Tab UI (Homepage / Products Wiki / Projects), Notion Projects sync
- v1.0 — Initial GitHub Pages deployment
