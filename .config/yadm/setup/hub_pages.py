"""converge hub pages: the fleet page (/) and one page per machine (/machine/<host>), plain HTML for the browser.

Rendered from the same functions the CLI prints with (sync.fleet_lines, sync.difference_lines, recipes.pending_lines),
so the page and `converge fleet` / `converge status` never disagree. No JS; one <style> block; light and dark.
"""
from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

import recipes
import snapshot
import sync

COMPARE = Path(__file__).parent / 'compare.yml'
STYLE = '''
:root{color-scheme:light dark;--bg:#fff;--fg:#1f2328;--dim:#656d76;--line:#d0d7de;
  --ok:#1a7f37;--changed:#0969da;--skipped:#656d76;--warn:#9a6700;--failed:#cf222e}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--dim:#8b949e;--line:#30363d;
  --ok:#3fb950;--changed:#58a6ff;--skipped:#8b949e;--warn:#d29922;--failed:#f85149}}
body{max-width:62rem;margin:0 auto;padding:1rem;background:var(--bg);color:var(--fg);
  font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
h1{font-size:1.4rem}h2{font-size:1.1rem;border-bottom:1px solid var(--line);padding-bottom:.2rem;margin-top:1.6rem}
h3{font-size:1rem;margin-bottom:0}a{color:var(--changed)}.dim{color:var(--dim)}
pre{font:13px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere}
pre.wide{white-space:pre;overflow-x:auto}ul{padding-left:0;list-style:none}li{margin:.3rem 0}li pre{margin:.2rem 0 0 1.6rem}
.ok{color:var(--ok)}.changed{color:var(--changed)}.skipped{color:var(--skipped)}.warn{color:var(--warn)}.failed{color:var(--failed)}
'''


def rules_for(every: bool) -> Dict[str, List[str]]:
    """compare.yml's rules, or every key for `?all=1` (as `converge fleet --diff --all`)."""
    return snapshot.EVERY_KEY if every else snapshot.load_compare(COMPARE)


def page(title: str, body: str) -> str:
    """A whole HTML document around already-escaped body markup."""
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><style>%s</style><body>%s</body></html>\n' % (escape(title), STYLE, body))


def pre(lines: List[str], wide: bool = False) -> str:
    """Lines in a <pre>; `wide` keeps alignment (tables) and scrolls sideways instead of wrapping."""
    return '<pre%s>%s</pre>' % (' class="wide"' if wide else '', escape('\n'.join(lines)))


def host_link(host: str, text: str) -> str:
    """A link to a machine's page, relative so it works at / and behind tailscale serve's /converge/."""
    return '<a href="machine/%s">%s</a>' % (escape(quote(host, safe='')), escape(text))


def fleet_table(rows: List[dict]) -> str:
    """sync.fleet_lines in a <pre>, each row's host turned into a link to its page."""
    lines = sync.fleet_lines(rows)
    if not lines:
        return '<p class="dim">No check-ins yet.</p>'
    cells = [host_link(row['host'], row['host']) + escape(line[len(row['host']):]) for row, line in zip(rows, lines)]
    cells += [escape(line) for line in lines[len(rows):]]  # the stale lines after the table
    return '<pre class="wide">%s</pre>' % '\n'.join(cells)


def pending_section(pending: List[dict]) -> str:
    """Pending recipes with numbered steps (recipes.pending_lines), or a calm line."""
    if not pending:
        return '<p class="dim">Nothing pending.</p>'
    return pre([line.lstrip('\n') for line in recipes.pending_lines(pending)])


def render_fleet(rows: List[dict], states: List[dict], every: bool = False) -> str:
    """The fleet page: who checked in, the drift between machines, every machine's pending recipes."""
    drift = sync.difference_lines(states, rules_for(every))
    toggle = '<a href="./">compare.yml keys only</a>' if every else '<a href="?all=1">every key</a>'
    parts = ['<h1>converge fleet</h1>', fleet_table(rows),
             '<h2>Drift</h2><p class="dim">%s · %s</p>' % (escape(drift[0]), toggle), pre(drift[1:], wide=True),
             '<h2>Pending recipes</h2>']
    waiting = [row for row in rows if row.get('pending')]
    for row in waiting:
        parts.append('<h3>%s</h3>%s' % (host_link(row['host'], row['host']), pending_section(row['pending'])))
    if not waiting:
        parts.append('<p class="dim">Nothing pending on any machine.</p>')
    return page('converge fleet', ''.join(parts))


def phase_items(phases: Dict[str, dict], every: bool) -> str:
    """One list item per phase, problems first: glyph and status word, key, summary, then its grouped detail lines
    (capped as in `converge status`; `every` lifts the cap like --all)."""
    calm_last = sorted(phases.items(), key=lambda kv: -list(sync.GLYPHS).index(kv[1]['status']))
    items = []
    for key, phase in calm_last:
        status = phase['status']
        lines, _ = sync.format_details(phase.get('details') or [], None if every else sync.DETAIL_LIMIT, indent='')
        items.append('<li><span class="%s">%s %s</span> <b>%s</b> %s%s</li>' % (
            status, sync.GLYPHS[status][0], status, escape(key), escape(phase.get('summary', '')), pre(lines) if lines else ''))
    return '<ul>%s</ul>' % ''.join(items)


def declared_lines(state: dict) -> List[str]:
    """`kind` then its grouped missing/undeclared entries, from the snapshot's declared.<kind>.missing/.undeclared lists."""
    kinds = sorted({key.split('.')[1] for key in state if key.startswith('declared.') and key.count('.') == 2})
    lines = []
    for kind in kinds:
        details = []
        for which in ('missing', 'undeclared'):
            entries = state.get('declared.%s.%s' % (kind, which))
            details += ['%s:%s' % (which, entry) for entry in entries or []]
        if details:
            lines += [kind] + sync.format_details(details)[0]
    return lines


def odd_keys(host: str, states: List[dict], rules: Dict[str, List[str]]) -> List[Tuple[str, object, object]]:
    """(key, this host's value, the majority's value) for each compared key where `host` differs from most of the other
    machines of its profile; a tie among the others has no majority and is not reported."""
    mine = [s for s in states if s['machine'].split('@', 1)[1] == host]
    if not mine:
        return []
    peers = [s for s in states if s.get('profile') == mine[0].get('profile')]
    odd = []
    for key, values in snapshot.differences(peers, rules):
        if host not in values:
            continue
        others = Counter(json.dumps(v, sort_keys=True) for h, v in values.items() if h != host)
        common, count = others.most_common(1)[0] if others else ('', 0)
        if count * 2 > sum(others.values()) and json.dumps(values[host], sort_keys=True) != common:
            odd.append((key, values[host], json.loads(common)))
    return odd


def odd_lines(odd: List[Tuple[str, object, object]]) -> List[str]:
    """odd_keys as aligned `key  here  fleet` lines (lists shown as what each side lacks, as in fleet --diff)."""
    if not odd:
        return []
    rows = [(key, {'here': mine, 'fleet': common}) for key, mine, common in odd]
    return snapshot.table(rows, ['here', 'fleet'])


def render_machine(host: str, found: dict, states: List[dict], every: bool = False) -> str:
    """One machine's page: its phases, declared gaps, pending recipes and the keys where it differs from the fleet."""
    last, state = found['last'], found['state']
    head = '%s · %s · exit %s · %s' % (last.get('machine', host), sync.age(last['finished']), last.get('exit', '?'), last.get('profile', '?'))
    odd = odd_lines(odd_keys(host, states, rules_for(every)))
    declared = declared_lines(state)
    parts = ['<p><a href="../">← fleet</a> · <a href="?all=1">all details and keys</a></p><h1>%s</h1><p class="dim">%s</p>' % (escape(host), escape(head)),
             '<h2>Phases</h2>', phase_items(last.get('phases') or {}, every),
             '<h2>Declared</h2>', pre(declared) if declared else '<p class="dim">Nothing missing or undeclared.</p>',
             '<h2>Pending recipes</h2>', pending_section(last.get('pending') or []),
             '<h2>Differs from the fleet</h2>', pre(odd, wide=True) if odd else '<p class="dim">Matches the majority of its profile.</p>']
    return page('converge · %s' % host, ''.join(parts))
