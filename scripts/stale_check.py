"""Keep one "The story may be out of date" issue listing what shipped in Trackaholic since the page was
last reviewed.

The bot never writes story content; this only flags it. Closing the issue means "handled up to here":
its body ends with <!-- through: N -->, and the next issue lists only pull requests merged after #N.
Before any issue has been closed, seed_through in sync-config.json is the starting point.

Usage: python scripts/stale_check.py [--page index.html] [--config sync-config.json] [--dry-run]
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

APP = 'Abdulla1x/Trackaholic'
STORY = os.environ.get('GITHUB_REPOSITORY', 'Abdulla1x/trackaholic-story')
LABEL = 'story-sync'
TITLE = 'The story may be out of date'
THROUGH = re.compile(r'<!-- through: (\d+) -->')


def gh(*args):
    return subprocess.run(['gh', *args], check=True, capture_output=True, text=True).stdout


def gh_json(*args):
    return json.loads(gh(*args))


def through_of(body):
    m = THROUGH.search(body or '')
    return int(m.group(1)) if m else None


def link(pr):
    return f"[#{pr['number']}](https://github.com/{APP}/pull/{pr['number']}) {pr['title']}"


def added_notes(prs, page):
    notes = []
    for pr in prs:
        files = gh_json('api', '--paginate', '--slurp', f"repos/{APP}/pulls/{pr['number']}/files")
        for f in (f for chunk in files for f in chunk):
            path = f['filename']
            # Engineering notes carry a year-month in their name (incident-2026-07-…, photo-size-ab-2026-10);
            # reference docs like docs/api.md don't, and don't belong on the story page.
            if f['status'] == 'added' and re.fullmatch(r'docs/[^/]*\d{4}-\d{2}[^/]*\.md', path) and path not in page:
                notes.append((path, pr))
    return notes


def build_body(new, all_prs, page, config, through):
    feats = [p for p in new if p['headRefName'].startswith('feat/')]
    rest = [p for p in new if p not in feats]
    out = ['Merged in Trackaholic since the story was last reviewed. Nothing here is changed automatically: '
           'update the page, or skip an item, then **close this issue** to mark everything below as handled.', '']

    out += ['### New features', *(f'- [ ] {link(p)}' for p in feats)] if feats else ['### New features', '- None']
    out.append('')

    notes = added_notes(new, page)
    if notes:
        out += ['### New engineering notes (not linked from the page)',
                *(f'- [ ] [`{path}`](https://github.com/{APP}/blob/main/{path}) from #{pr["number"]}' for path, pr in notes), '']

    hits = []
    for card, words in config['cards'].items():
        matched = [p for p in new if any(w in f"{p['title']} {p['headRefName']}".lower() for w in words)]
        if matched:
            hits.append(f"- [ ] **{card}**: {', '.join('#%d' % p['number'] for p in matched)}")
    if hits:
        out += ["### \"Where it's going\" cards that may need trimming", *hits, '']

    tags = re.findall(r'<(?:h3|b)>([^<]+)</(?:h3|b)>(?:(?!<(?:h3|b)>).){0,400}?<span class="pend">([^<]+)</span>', page, re.S)
    if tags:
        out += ['### Waiting tags on the page']
        out += [f"- **{tag}** on \"{where}\". {config['pending'].get(tag, '')}".rstrip() for where, tag in tags]
        out.append('')

    cps = re.findall(r"\{ id: '([^']+)', date: '(\d{4}-\d{2}-\d{2})', title: '([^']+)'", page)
    if cps:
        cid, cdate, ctitle = cps[-1]
        days = (dt.date.today() - dt.date.fromisoformat(cdate)).days
        since = [p for p in all_prs if p['headRefName'].startswith('feat/') and p['mergedAt'][:10] > cdate]
        out += ['### Screenshots',
                f'Last checkpoint: **{ctitle}** ({cdate}, {days} days ago). '
                f'{len(since)} feature pull request{"s" if len(since) != 1 else ""} merged since.', '']

    if rest:
        out += ['<details><summary>Fixes, docs and chores (%d)</summary>' % len(rest), '',
                *(f'- {link(p)}' for p in rest), '', '</details>', '']

    out.append(f'<!-- through: {through} -->')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default='index.html')
    ap.add_argument('--config', default='sync-config.json')
    ap.add_argument('--dry-run', action='store_true', help='print the issue body instead of touching issues')
    args = ap.parse_args()

    page = Path(args.page).read_text(encoding='utf-8')
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))

    closed = gh_json('issue', 'list', '-R', STORY, '--label', LABEL, '--state', 'closed', '--limit', '1', '--json', 'body')
    base = (closed and through_of(closed[0]['body'])) or config['seed_through']
    opened = gh_json('issue', 'list', '-R', STORY, '--label', LABEL, '--state', 'open', '--limit', '1', '--json', 'number,body')

    all_prs = gh_json('pr', 'list', '-R', APP, '--state', 'merged', '--limit', '5000',
                      '--json', 'number,title,headRefName,mergedAt')
    new = sorted((p for p in all_prs if p['number'] > base), key=lambda p: p['number'])
    if not new:
        print(f'Nothing merged after #{base}.')
        return
    through = new[-1]['number']
    body = build_body(new, all_prs, page, config, through)

    if args.dry_run:
        print(body)
        return

    if not opened:
        gh('label', 'create', LABEL, '-R', STORY, '--color', '5319e7', '--force',
           '--description', 'Trackaholic changes the story page may need')
        print(gh('issue', 'create', '-R', STORY, '--title', TITLE, '--label', LABEL, '--body', body).strip())
        return

    issue = opened[0]
    prev = through_of(issue['body']) or base
    if issue['body'].strip() != body.strip():
        gh('issue', 'edit', str(issue['number']), '-R', STORY, '--body', body)
    fresh = [p for p in new if p['number'] > prev]
    if fresh:
        # Edits don't send email; a comment does.
        gh('issue', 'comment', str(issue['number']), '-R', STORY, '--body',
           'New since the last update:\n' + '\n'.join(f'- {link(p)}' for p in fresh))
    print(f"Issue #{issue['number']} updated, {len(fresh)} new.")


if __name__ == '__main__':
    sys.exit(main())
