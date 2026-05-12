#!/usr/bin/env python3
"""Fetch active NOKIA projects from Notion → write notion-projects.json.

Runs in GitHub Actions on a schedule. Requires env var NOTION_TOKEN.
Filter: CATEGORY != PERSONAL (includes NOKIA + uncategorized) AND Status is active.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
DATABASE_ID = '1fa9e3a8-1ab3-8122-9969-faa4690dbfc7'
NOTION_API = f'https://api.notion.com/v1/databases/{DATABASE_ID}/query'
NOTION_VERSION = '2022-06-28'

# Statuses considered "active" — matches the Active view in Notion
ACTIVE_STATUSES = [
    'Planning',
    'In Progress',
    'Deployment',
    'Business Development',
    'RFP Preparation',
    'Bid Submitted',
    'Bid Awarded',
]


def query_notion():
    if not NOTION_TOKEN:
        sys.exit('ERROR: NOTION_TOKEN env var not set')

    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }
    body = {
        'filter': {
            'and': [
                # NOKIA or uncategorized (exclude PERSONAL)
                {
                    'or': [
                        {'property': 'CATEGORY', 'select': {'equals': 'NOKIA'}},
                        {'property': 'CATEGORY', 'select': {'is_empty': True}},
                    ]
                },
                # Active statuses
                {
                    'or': [
                        {'property': 'Status', 'status': {'equals': s}}
                        for s in ACTIVE_STATUSES
                    ]
                },
            ]
        },
        'page_size': 100,
    }

    all_results = []
    while True:
        req = urllib.request.Request(
            NOTION_API,
            data=json.dumps(body).encode(),
            headers=headers,
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f'Notion API error: {e.code} {e.reason}', file=sys.stderr)
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


def transform(row):
    props = row.get('properties', {})

    latest_bom = get_text(props.get('Latest BOM'))
    # Users sometimes paste paths with surrounding quotes — strip them
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
        'url': row.get('url', ''),
    }
    # Drop empty fields for cleaner JSON
    return {k: v for k, v in out.items() if v}


def main():
    rows = query_notion()
    projects = [transform(r) for r in rows]
    projects = [p for p in projects if p.get('name')]  # safety

    # Sort: priority High > Medium > Low > unset, then name A-Z
    prio_order = {'High': 0, 'Medium': 1, 'Low': 2}
    projects.sort(key=lambda p: (prio_order.get(p.get('priority', ''), 99), p.get('name', '')))

    # Vietnam time (ICT, UTC+7) for the date label
    today_ict = datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d')

    output = {
        'lastSync': today_ict,
        'source': 'Notion — MY PROJECTS · NOKIA active (auto-synced)',
        'count': len(projects),
        'projects': projects,
    }

    out_path = os.environ.get('OUTPUT_PATH', 'notion-projects.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'Wrote {len(projects)} projects to {out_path}')


if __name__ == '__main__':
    main()
