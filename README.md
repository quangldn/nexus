# Nexus Dashboard — v0

A single-file HTML dashboard for quick access to your most-used links (SharePoint, OneDrive, Notion, product slides, ngCRM, etc.).

## Files
- `dashboard.html` — the dashboard. Open it in Edge.
- `README.md` — this note.

## How to use it on the Nokia laptop
1. Copy `dashboard.html` to a stable location on the Nokia laptop, e.g. `C:\Users\<you>\Documents\Nexus\dashboard.html`.
2. Open it once in Edge to confirm it loads.
3. Set as Edge homepage:
   - Edge → Settings → Start, home, and new tabs
   - Under "Home button" → toggle on → enter `file:///C:/Users/<you>/Documents/Nexus/dashboard.html`
   - Under "When Edge starts" → "Open these pages" → add the same `file:///...` URL
4. Pin the Home button to the toolbar for one-click access.

## How to add or edit links
1. Open `dashboard.html` in Notepad or VS Code (anything that edits text).
2. Find the block that starts with `<script type="application/json" id="dashboard-data">`.
3. Inside, edit the JSON. Structure:
   ```json
   {
     "name": "Category name",
     "icon": "📁",
     "links": [
       { "title": "Display name", "url": "https://...", "note": "optional context", "hot": true }
     ]
   }
   ```
   - `note` is optional small grey text under the title.
   - `hot` is optional — set to `true` to add a yellow left-bar flag (use it for things you must check this week).
4. Update the `lastEdited` field at the top to today's date.
5. Save, refresh the dashboard in Edge.

If the JSON has a syntax error (missing comma, unclosed quote), the dashboard will show an error message telling you what's wrong instead of going blank.

## Keyboard
- `Ctrl + K` — focus the search box.
- `Esc` — clear search.

## Transferring updates between laptops
Edit on personal laptop with Claude → send `dashboard.html` over your IM → drop into the Nokia laptop folder, overwrite. Done.

## Roadmap (later versions)
- v1: Recent projects section (project name → latest BOM, slides, quote status).
- v2: Static snapshot of your Notion project DB embedded as a filterable table.
- v3: Drag-to-add support if you want it.
