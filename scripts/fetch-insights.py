#!/usr/bin/env python3
"""Fetch Published posts from 'My Insights' Notion DB.

Writes:
  - notion-posts.json (index: title/summary/tags/date/important/notionUrl/bodyFile)
  - posts/<slug>-<id8>.md  (one markdown file per Published page)

Cleans posts/*.md before writing — only Published-and-current posts are kept.

Run in GitHub Actions. Requires NOTION_TOKEN env var.
"""

import glob
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = '3609e3a8-1ab3-80b0-88bd-f313b3229eec'  # My Insights wiki DB (from URL page ID)
NOTION_VERSION = '2022-06-28'
POSTS_DIR = os.environ.get('POSTS_DIR', 'posts')
INDEX_PATH = os.environ.get('INDEX_PATH', 'notion-posts.json')


def _headers():
    if not NOTION_TOKEN:
        sys.exit('ERROR: NOTION_TOKEN env var not set')
    return {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }


def _api(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f'Notion API {method} {url} -> {e.code} {e.reason}', file=sys.stderr)
        try:
            print(e.read().decode(), file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)


def query_db():
    url = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
    body = {
        'filter': {'property': 'Status', 'status': {'equals': 'Published'}},
        'sorts': [{'property': 'Last edited time', 'direction': 'descending'}],
        'page_size': 100,
    }
    out = []
    while True:
        data = _api('POST', url, body)
        out.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        body['start_cursor'] = data['next_cursor']
    return out


def fetch_blocks(block_id):
    """Fetch direct children of a block. Recursive children fetched on demand."""
    blocks = []
    cursor = None
    while True:
        url = f'https://api.notion.com/v1/blocks/{block_id}/children?page_size=100'
        if cursor:
            url += f'&start_cursor={cursor}'
        data = _api('GET', url)
        blocks.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        cursor = data['next_cursor']
    return blocks


# === Property accessors ===
def get_title(prop):
    if not prop or not prop.get('title'): return ''
    return ''.join(t.get('plain_text', '') for t in prop['title']).strip()

def get_text(prop):
    if not prop or not prop.get('rich_text'): return ''
    return ''.join(t.get('plain_text', '') for t in prop['rich_text']).strip()

def get_multi_select(prop):
    if not prop or prop.get('multi_select') is None: return []
    return [s.get('name', '') for s in prop['multi_select']]

def get_checkbox(prop):
    if not prop: return False
    return bool(prop.get('checkbox', False))

def get_date(prop):
    if not prop or not prop.get('date') or not prop['date']:
        return ''
    return prop['date'].get('start', '') or ''


# === Rich text inline → markdown ===
def render_rich(rich_list):
    out = []
    for rt in (rich_list or []):
        text = rt.get('plain_text', '')
        if not text:
            continue
        # Escape markdown control chars only minimally (preserve user intent)
        ann = rt.get('annotations', {}) or {}
        href = rt.get('href')
        if ann.get('code'):
            text = f'`{text}`'
        if ann.get('bold'):
            text = f'**{text}**'
        if ann.get('italic'):
            text = f'*{text}*'
        if ann.get('strikethrough'):
            text = f'~~{text}~~'
        if href:
            text = f'[{text}]({href})'
        out.append(text)
    return ''.join(out)


# === Block → markdown ===
def block_inline(block, indent=0):
    """Render a single block's own text (no children). Returns string or empty."""
    t = block.get('type')
    data = block.get(t, {})
    pad = '  ' * indent

    if t == 'paragraph':
        return pad + render_rich(data.get('rich_text'))

    if t in ('heading_1', 'heading_2', 'heading_3'):
        level = int(t.split('_')[1])
        return '#' * level + ' ' + render_rich(data.get('rich_text'))

    if t == 'bulleted_list_item':
        return pad + '- ' + render_rich(data.get('rich_text'))

    if t == 'numbered_list_item':
        return pad + '1. ' + render_rich(data.get('rich_text'))

    if t == 'to_do':
        mark = '[x]' if data.get('checked') else '[ ]'
        return pad + f'- {mark} ' + render_rich(data.get('rich_text'))

    if t == 'quote':
        text = render_rich(data.get('rich_text'))
        return '\n'.join('> ' + ln for ln in (text.split('\n') if text else ['']))

    if t == 'callout':
        icon_obj = data.get('icon') or {}
        prefix = ''
        if icon_obj.get('type') == 'emoji':
            prefix = icon_obj.get('emoji', '') + ' '
        return '> ' + prefix + render_rich(data.get('rich_text'))

    if t == 'code':
        lang = (data.get('language') or '').replace('plain text', '').strip()
        code = ''.join(rt.get('plain_text', '') for rt in (data.get('rich_text') or []))
        return f'```{lang}\n{code}\n```'

    if t == 'divider':
        return '---'

    if t == 'image':
        f = data.get('file') or data.get('external') or {}
        url = f.get('url', '')
        caption = render_rich(data.get('caption', [])) or 'image'
        return f'![{caption}]({url})'

    if t in ('bookmark', 'embed', 'link_preview'):
        url = data.get('url', '')
        return f'[{url}]({url})'

    if t in ('file', 'pdf'):
        f = data.get('file') or data.get('external') or {}
        url = f.get('url', '')
        caption = render_rich(data.get('caption', [])) or 'file'
        return f'[{caption}]({url})'

    if t == 'video':
        f = data.get('file') or data.get('external') or {}
        return f'[Video]({f.get("url", "")})'

    if t == 'equation':
        return f'$$\n{data.get("expression", "")}\n$$'

    if t == 'toggle':
        return pad + render_rich(data.get('rich_text'))

    if t in ('synced_block', 'column_list', 'column', 'breadcrumb', 'table_of_contents'):
        return ''

    if t == 'unsupported':
        return '_(unsupported block)_'

    if 'rich_text' in data:
        return pad + render_rich(data.get('rich_text'))

    return ''


def render_blocks(blocks, indent=0):
    """Render a flat list of blocks into one markdown string. Recurses into children."""
    parts = []
    for block in blocks:
        t = block.get('type')

        # Tables: render rows from children
        if t == 'table':
            children = fetch_blocks(block['id']) if block.get('has_children') else []
            tdata = block.get('table', {}) or {}
            has_header = tdata.get('has_column_header', False)
            rows = []
            for c in children:
                if c.get('type') == 'table_row':
                    cells = c.get('table_row', {}).get('cells', [])
                    rendered = [render_rich(cell) for cell in cells]
                    rows.append('| ' + ' | '.join(rendered) + ' |')
            if rows:
                if has_header and len(rows) >= 1:
                    cols = rows[0].count('|') - 1
                    sep = '|' + '|'.join([' --- '] * cols) + '|'
                    rows.insert(1, sep)
                parts.append('\n'.join(rows))
            continue

        if t == 'table_row':
            # Already handled by parent table; skip
            continue

        md = block_inline(block, indent)
        if md:
            parts.append(md)

        if block.get('has_children'):
            children = fetch_blocks(block['id'])
            if children:
                sub_indent = indent + 1 if t in (
                    'bulleted_list_item', 'numbered_list_item', 'to_do', 'toggle'
                ) else indent
                child_md = render_blocks(children, sub_indent)
                if child_md:
                    parts.append(child_md)

    return '\n\n'.join(p for p in parts if p and p.strip())


def slug(s, max_len=40):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:max_len]


def transform(row):
    props = row.get('properties', {}) or {}
    page_id = row.get('id', '')
    return {
        '_page_id': page_id,
        'id': page_id.replace('-', ''),
        'title': get_title(props.get('Title')),
        'summary': get_text(props.get('Summary')),
        'tags': get_multi_select(props.get('Tags')),
        'category': get_multi_select(props.get('Category')),
        'date': get_date(props.get('Date')),
        'important': get_checkbox(props.get('Important')),
        'lastEdited': row.get('last_edited_time', ''),
        'notionUrl': row.get('url', ''),
    }


def clean_posts_dir():
    """Delete all .md files in POSTS_DIR (auto-managed by sync)."""
    os.makedirs(POSTS_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(POSTS_DIR, '*.md')):
        try:
            os.remove(f)
        except OSError as e:
            print(f'Warning: could not delete {f}: {e}', file=sys.stderr)


def main():
    rows = query_db()
    print(f'Notion returned {len(rows)} Published row(s) from My Insights DB.', file=sys.stderr)

    clean_posts_dir()

    posts = []
    for row in rows:
        meta = transform(row)
        if not meta['title']:
            continue
        try:
            blocks = fetch_blocks(meta['_page_id'])
            md_body = render_blocks(blocks)
        except SystemExit:
            raise
        except Exception as e:
            print(f'Warning: failed to fetch blocks for "{meta["title"]}": {e}', file=sys.stderr)
            md_body = ''

        # Body file: title-h1 + summary blockquote + content
        body_parts = [f"# {meta['title']}"]
        if meta['summary']:
            body_parts.append(f"> {meta['summary']}")
        if md_body:
            body_parts.append(md_body)
        body = '\n\n'.join(body_parts) + '\n'

        s = slug(meta['title'])
        short_id = meta['id'][:8]
        fname = f'{s}-{short_id}.md' if s else f'{short_id}.md'
        with open(os.path.join(POSTS_DIR, fname), 'w', encoding='utf-8') as f:
            f.write(body)

        merged_tags = []
        for tg in (meta['category'] or []):
            if tg and tg not in merged_tags:
                merged_tags.append(tg)
        for tg in (meta['tags'] or []):
            if tg and tg not in merged_tags:
                merged_tags.append(tg)

        post = {
            'id': meta['id'],
            'title': meta['title'],
            'summary': meta['summary'],
            'tags': merged_tags,
            'date': meta['date'],
            'important': meta['important'],
            'lastEdited': meta['lastEdited'],
            'notionUrl': meta['notionUrl'],
            'bodyFile': f'{POSTS_DIR}/{fname}',
        }
        # Drop empty optional fields but always keep `important` (False is meaningful)
        cleaned = {}
        for k, v in post.items():
            if k == 'important':
                if v: cleaned[k] = v
            elif v not in (None, '', [], {}):
                cleaned[k] = v
        posts.append(cleaned)

    today_ict = datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M ICT')
    output = {
        'lastSync': today_ict,
        'source': 'Notion — My Insights · Published (auto-synced)',
        'count': len(posts),
        'posts': posts,
    }
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f'Wrote {len(posts)} post(s) to {INDEX_PATH} and {POSTS_DIR}/', file=sys.stderr)


if __name__ == '__main__':
    main()
