#!/usr/bin/env python3
"""Fetch from Notion → write notion-projects.json AND notion-documents.json.

Runs in GitHub Actions on a schedule. Requires env var NOTION_TOKEN.

PROJECTS DB:
  Filter: CATEGORY != PERSONAL (NOKIA + uncategorized) AND Status is active.
DOCUMENT VAULT DB:
  All rows. Resolves 1830 Portfolio relation IDs to page titles.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_VERSION = '2022-06-28'

PROJECTS_DB_ID = '1fa9e3a8-1ab3-8122-9969-faa4690dbfc7'
DOCUMENTS_DB_ID = '35e9e3a8-1ab3-8043-bfd1-000bb57bb2a3'
PORTFOLIO_DB_ID = '2859e3a8-1ab3-808d-a825-000bb170b359'

# Statuses considered "active" for projects
ACTIVE_STATUSES = [
    'Planning',
    'In Progress',
    'Deployment',
    'Business Development',
    'RFP Preparation',
    'Bid Submitted',
    'Bid Awarded',
]


# --------------------------------------------------------------------------
# Notion API helpers
# --------------------------------------------------------------------------

def _headers():
    if not NOTION_TOKEN:
        sys.exit('ERROR: NOTION_TOKEN env var not set')
    return {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }


def _query_db(db_id, body=None):
    """Paginated POST to Notion DB query. Returns all results."""
    url = f'https://api.notion.com/v1/databases/{db_id}/query'
    if body is None:
        body = {}
    body.setdefault('page_size', 100)
    all_results = []
    while True:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers=_headers(),
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f'Notion API error querying {db_id}: {e.code} {e.reason}', file=sys.stderr)
            try:
                print(e.read().decode(), file=sys.stderr)
            except Exception:
                pass
            sys.exit(1)
        all_results.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        body['start_cursor'] = data['next_cursor']
    return all_results


# --------------------------------------------------------------------------
# Property extractors
# --------------------------------------------------------------------------

def get_title(prop):
    if not prop or not prop.get('title'):
        return ''
    return ''.join(t.get('plain_text', '') for t in prop['title']).strip()


def get_text(prop):
    if not prop or not prop.get('rich_text'):
        return ''
    return ''.join(t.get('plain_text', '') for t in prop['rich_text']).strip()


def get_select(prop):
    if not prop or not prop.get('select'):
        return ''
    return prop['select'].get('name', '') if prop['select'] else ''


def get_status(prop):
    if not prop or not prop.get('status'):
        return ''
    return prop['status'].get('name', '') if prop['status'] else ''


def get_multi_select(prop):
    if not prop or not prop.get('multi_select'):
        return []
    return [s.get('name', '') for s in prop['multi_select']]


def get_url(prop):
    if not prop:
        return ''
    return prop.get('url') or ''


def get_checkbox(prop):
    if not prop:
        return False
    return bool(prop.get('checkbox'))


def get_relation_ids(prop):
    if not prop or not prop.get('relation'):
        return []
    return [r.get('id', '') for r in prop['relation'] if r.get('id')]


def _epoch(iso_str):
    if not iso_str:
        return 0
    try:
        s = iso_str.replace('Z', '+00:00')
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, AttributeError):
        return 0


# --------------------------------------------------------------------------
# PROJECTS
# --------------------------------------------------------------------------

def fetch_projects():
    body = {
        'filter': {
            'and': [
                {
                    'or': [
                        {'property': 'CATEGORY', 'select': {'equals': 'NOKIA'}},
                        {'property': 'CATEGORY', 'select': {'is_empty': True}},
                    ]
                },
                {
                    'or': [
                        {'property': 'Status', 'status': {'equals': s}}
                        for s in ACTIVE_STATUSES
                    ]
                },
            ]
        },
    }
    return _query_db(PROJECTS_DB_ID, body)


def transform_project(row):
    props = row.get('properties', {})
    latest_bom = get_text(props.get('Latest BOM'))
    if latest_bom.startswith('"') and latest_bom.endswith('"'):
        latest_bom = latest_bom[1:-1]
    customers = ', '.join(get_multi_select(props.get('Customer')))
    out = {
        'name': get_title(props.get('Project Name')),
        'status': get_status(props.get('Status')),
        'priority': get_select(props.get('Priority')),
        'customer': customers,
        'lineSystem': get_select(props.get('Line System')),
        'bom': get_select(props.get('BoM')),
        'projectType': get_select(props.get('Project Type')),
        'keyUpdate': get_text(props.get('Key Update')),
        'description': get_text(props.get('Description')),
        'latestBom': latest_bom,
        'lastEdited': row.get('last_edited_time', ''),
        'url': row.get('url', ''),
    }
    return {k: v for k, v in out.items() if v}


def write_projects():
    rows = fetch_projects()
    projects = [transform_project(r) for r in rows]
    projects = [p for p in projects if p.get('name')]

    prio_order = {'High': 0, 'Medium': 1, 'Low': 2}
    projects.sort(key=lambda p: (
        -1 * _epoch(p.get('lastEdited', '')),
        prio_order.get(p.get('priority', ''), 99),
        p.get('name', ''),
    ))

    today_ict = datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d')
    output = {
        'lastSync': today_ict,
        'source': 'Notion — MY PROJECTS · NOKIA active (auto-synced)',
        'count': len(projects),
        'projects': projects,
    }
    out_path = os.environ.get('PROJECTS_OUTPUT_PATH', 'notion-projects.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(projects)} projects to {out_path}')


# --------------------------------------------------------------------------
# DOCUMENT VAULT
# --------------------------------------------------------------------------

def fetch_portfolio_map():
    """Returns {page_id: title} for the 1830 Portfolio DB."""
    rows = _query_db(PORTFOLIO_DB_ID)
    out = {}
    for r in rows:
        rid = r.get('id', '').replace('-', '')
        if not rid:
            continue
        # Title property is "Name"
        props = r.get('properties', {})
        title = get_title(props.get('Name'))
        if title:
            out[rid] = title
    return out


def transform_document(row, portfolio_map):
    props = row.get('properties', {})
    # Resolve portfolio relation IDs to titles
    rel_ids = get_relation_ids(props.get('1830 Portfolio'))
    portfolio = []
    for rid in rel_ids:
        norm = rid.replace('-', '')
        name = portfolio_map.get(norm)
        if name and name not in portfolio:
            portfolio.append(name)

    out = {
        'name': get_title(props.get('Document Name')),
        'url': get_url(props.get('URL')),
        'description': get_text(props.get('Description')),
        'portfolio': portfolio,
        'tags': get_multi_select(props.get('Tags')),
        'important': get_checkbox(props.get('Important')),
        'lastEdited': row.get('last_edited_time', ''),
    }
    return out


def write_documents():
    portfolio_map = fetch_portfolio_map()
    rows = _query_db(DOCUMENTS_DB_ID)
    docs = [transform_document(r, portfolio_map) for r in rows]
    docs = [d for d in docs if d.get('name')]
    # Sort: important first, then name
    docs.sort(key=lambda d: (
        0 if d.get('important') else 1,
        d.get('name', '').lower(),
    ))

    today_ict = datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d')
    output = {
        'lastSync': today_ict,
        'source': 'Notion — Document Vault (auto-synced)',
        'count': len(docs),
        'documents': docs,
    }
    out_path = os.environ.get('DOCUMENTS_OUTPUT_PATH', 'notion-documents.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(docs)} documents to {out_path}')


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

def main():
    write_projects()
    write_documents()


if __name__ == '__main__':
    main()
