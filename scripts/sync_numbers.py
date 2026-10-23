"""Recount the page's numbers from the Trackaholic repository and write them into index.html.

Only numbers change: commits (facts row, running total, chart data, chart labels, the July-October
sentence), merged pull requests, and backend tests rounded down to the hundred. Every replacement is
anchored to the text around it and fails loudly when that text is gone, so a reworded page stops the
sync instead of being edited in the wrong place (NOTE_TOTAL = 765 in the How it started script is a
pixel offset, not the commit count).

Usage: python scripts/sync_numbers.py --trackaholic <checkout> [--page index.html] [--prs N]
       [--tests N | --no-tests] [--summary out.md]
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = 'Abdulla1x/Trackaholic'
FIRST_MONTH = '2024-07'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def months_between(first, last):
    y, m = map(int, first.split('-'))
    ly, lm = map(int, last.split('-'))
    out = []
    while (y, m) <= (ly, lm):
        out.append(f'{y:04d}-{m:02d}')
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_name(ym):
    y, m = ym.split('-')
    return f'{MON[int(m) - 1]} {y}'


def count_commits(checkout):
    # Author dates in each author's own zone, the same way the page's chart was first counted.
    dates = run(['git', 'log', 'HEAD', '--format=%ad', '--date=format:%Y-%m'], cwd=checkout).split()
    per = Counter(dates)
    months = months_between(FIRST_MONTH, max(dates))
    return len(dates), [(ym, per.get(ym, 0)) for ym in months]


def count_prs():
    out = run(['gh', 'pr', 'list', '-R', REPO, '--state', 'merged', '--limit', '5000', '--json', 'number'])
    return len(json.loads(out))


def count_tests(checkout):
    out = run([sys.executable, '-m', 'pytest', '--collect-only', '-q'], cwd=Path(checkout) / 'backend')
    m = re.search(r'(\d+) tests? collected', out)
    if not m:
        sys.exit('pytest --collect-only printed no "N tests collected" line')
    return int(m.group(1))


def commits_js(series):
    # Same layout as the hand-written array: ten months on the first line, twelve on each after.
    items = [f"['{ym}', {n}]" for ym, n in series]
    lines = [items[:10]] + [items[i:i + 12] for i in range(10, len(items), 12)]
    body = ',\n    '.join(', '.join(line) for line in lines)
    return f'var COMMITS = [{body}];'


class Page:
    def __init__(self, text):
        self.text = text
        self.changes = []

    def sub(self, label, pattern, repl, count=1):
        new, n = re.subn(pattern, repl, self.text, flags=re.S)
        if n != count:
            sys.exit(f'{label}: expected {count} match(es) for {pattern!r}, found {n}. Has the page been reworded?')
        if new != self.text:
            self.changes.append(label)
        self.text = new

    def get(self, pattern):
        m = re.search(pattern, self.text, flags=re.S)
        if not m:
            sys.exit(f'Could not read {pattern!r} from the page')
        return m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trackaholic', required=True, help='a full-history checkout of Trackaholic')
    ap.add_argument('--page', default='index.html')
    ap.add_argument('--prs', type=int, help='merged PR count (default: ask gh)')
    ap.add_argument('--tests', type=int, help='collected test count (default: run pytest)')
    ap.add_argument('--no-tests', action='store_true', help="leave the test count as it is")
    ap.add_argument('--summary', help='write an old -> new list here for the pull request')
    args = ap.parse_args()

    total, series = count_commits(args.trackaholic)
    prs = args.prs if args.prs is not None else count_prs()
    tests = None if args.no_tests else (args.tests if args.tests is not None else count_tests(args.trackaholic))
    last = month_name(series[-1][0])
    summer = sum(n for ym, n in series if '2026-07' <= ym <= '2026-10')

    path = Path(args.page)
    page = Page(path.read_text(encoding='utf-8'))
    before = {
        'Commits': page.get(r'<span class="lbl">Commits</span><span class="v num" data-count="(\d+)"'),
        'Merged pull requests': page.get(r'<b class="num">(\d+)</b><span>merged pull requests'),
        'Backend tests': page.get(r'<b class="num">([\d,]+)</b><span>backend tests'),
        'Chart ends': page.get(r'Commits per month, Jul 2024 to (\w+ \d{4})'),
    }

    page.sub('facts row commits',
             r'(<span class="lbl">Commits</span><span class="v num" data-count=")\d+(">)\d+(</span>)',
             rf'\g<1>{total}\g<2>{total}\g<3>')
    page.sub('running total', r'(<p class="runtot num" id="runtot"[^>]*><b>)\d+(</b><span>commits by )\w+ \d{4}(</span>)',
             rf'\g<1>{total}\g<2>{last}\g<3>')
    page.sub('chart label', r'(Commits per month, Jul 2024 to )\w+ \d{4}', rf'\g<1>{last}')
    page.sub('chart note', r'\d+ of the \d+( commits landed between July and October)', rf'{summer} of the {total}\g<1>')
    page.sub('chart data', r"var COMMITS = \[\['2024-07'.*?\]\];", commits_js(series).replace('\\', r'\\'))
    page.sub('cycles pull requests', r'(<span data-count=")\d+(">)\d+(</span> pull requests)', rf'\g<1>{prs}\g<2>{prs}\g<3>')
    page.sub('practice pull requests', r'(<b class="num">)\d+(</b><span>merged pull requests)', rf'\g<1>{prs}\g<2>')
    if tests is not None:
        page.sub('backend tests', r'(<b class="num">)[\d,]+(</b><span>backend tests)', rf'\g<1>{tests // 100 * 100:,}\g<2>')

    after = {'Commits': str(total), 'Merged pull requests': str(prs),
             'Backend tests': before['Backend tests'] if tests is None else f'{tests // 100 * 100:,}', 'Chart ends': last}

    if page.changes:
        path.write_text(page.text, encoding='utf-8')
    lines = [f'- {k}: {before[k]} → {after[k]}' for k in before if before[k] != after[k]]
    if page.changes and not lines:
        lines = ['- Monthly commit counts in the chart']
    if tests is not None:
        lines.append(f'\n{tests:,} tests collected, shown rounded down to the hundred.')
    print('\n'.join(lines) if page.changes else 'Numbers are current.')
    if args.summary and page.changes:
        Path(args.summary).write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
