#!/usr/bin/env python3
"""converge hub: stores every machine's check-in and answers `converge fleet` (runs on home-gpu, user systemd unit).

Clients POST {"last": last.json, "state": state.json} to /report through `tailscale serve`, which adds the
Tailscale-User-Login header; the cluster, off the tailnet, still force-pushes a status/* branch, which the bridge
thread fetches with git. One sqlite table holds every report for 90 days. Stdlib only, Python 3.9 syntax.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple
from urllib.parse import unquote, urlsplit

import sync

PORT = 8790
DB = '.local/state/dotfiles/hub.sqlite'
BRIDGE_DIR = '.local/state/dotfiles/hub-bridge'  # bare clone of the remote, status/* branches only
REMOTE = 'https://github.com/jyesselm/dotfiles.git'  # public: plain git, no gh login needed
BRIDGE_INTERVAL_S = 30 * 60
PREFIX = '/converge'  # `tailscale serve --set-path /converge` may forward the prefix
STALE_DAYS = 2
KEEP_DAYS = 90
MAX_BODY = 2 * 1024 * 1024
GIT_TIMEOUT_S = 300
SCHEMA = '''
CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, host TEXT, class TEXT, profile TEXT, finished TEXT,
                                    exit INTEGER, received TEXT, last_json TEXT, state_json TEXT);
CREATE INDEX IF NOT EXISTS reports_host ON reports (host, received);
'''
NEWEST = '''SELECT * FROM reports r WHERE id = (SELECT id FROM reports WHERE host = r.host ORDER BY finished DESC, id DESC LIMIT 1)
            ORDER BY finished DESC'''
JSON, TEXT, PAGE = 'application/json', 'text/plain; charset=utf-8', 'text/html; charset=utf-8'


class Reply(NamedTuple):
    """What a route answers: HTTP status, body text and Content-Type."""
    status: int
    body: str
    kind: str


@dataclass
class HubConfig:
    """What every request handler needs: the database path and whether direct (non-tailscale-serve) posts count."""
    db: Path
    trust_local: bool = False


def now() -> datetime:
    """The current UTC time (received stamps, staleness, pruning)."""
    return datetime.now(timezone.utc)


def connect(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the reports database; one connection per thread."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(SCHEMA)
    return db


def validate_last(last: dict) -> Tuple[str, str]:
    """(class, host) of a last.json (`machine` is `class@host`); ValueError for anything that is not one."""
    machine = last.get('machine') if isinstance(last, dict) else None
    if not isinstance(machine, str) or '@' not in machine:
        raise ValueError('last.machine must be "class@host"')
    if not isinstance(last.get('phases'), dict):
        raise ValueError('last.phases must be an object')
    datetime.fromisoformat(str(last.get('finished')))  # ValueError when absent or malformed
    cls, host = machine.split('@', 1)
    return cls, host


def store_report(db: sqlite3.Connection, last: dict, state: dict) -> None:
    """Insert one check-in, then prune old rows; ValueError when `last` is not a last.json."""
    cls, host = validate_last(last)
    row = (host, cls, last.get('profile', '?'), last['finished'], int(last.get('exit', 1)), now().isoformat(),
           json.dumps(last), json.dumps(state or {}))
    with db:
        db.execute('INSERT INTO reports (host, class, profile, finished, exit, received, last_json, state_json) '
                   'VALUES (?, ?, ?, ?, ?, ?, ?, ?)', row)
    prune(db, KEEP_DAYS)


def prune(db: sqlite3.Connection, days: int) -> int:
    """Delete reports received more than `days` ago; how many went."""
    cutoff = (now() - timedelta(days=days)).isoformat()
    with db:
        return db.execute('DELETE FROM reports WHERE received < ?', (cutoff,)).rowcount


def is_stale(finished: str) -> bool:
    """True when a run finished more than STALE_DAYS ago."""
    return datetime.fromisoformat(finished) < now() - timedelta(days=STALE_DAYS)


def fleet_rows(db: sqlite3.Connection) -> List[dict]:
    """Newest report per host, newest first, in the shape sync.fleet_lines prints."""
    rows = []
    for row in db.execute(NEWEST):
        phases = {key: phase['status'] for key, phase in json.loads(row['last_json'])['phases'].items()}
        rows.append({'host': row['host'], 'class': row['class'], 'profile': row['profile'], 'finished': row['finished'],
                     'exit': row['exit'], 'received': row['received'], 'phases': phases,
                     'corrective': sync.corrective(phases.values()), 'stale': is_stale(row['finished'])})
    return rows


def machine(db: sqlite3.Connection, host: str) -> Optional[dict]:
    """{'last': ..., 'state': ...} of a host's newest report, or None for a host never seen."""
    row = db.execute('SELECT last_json, state_json FROM reports WHERE host = ? ORDER BY finished DESC, id DESC LIMIT 1',
                     (host,)).fetchone()
    if row is None:
        return None
    return {'last': json.loads(row['last_json']), 'state': json.loads(row['state_json'])}


def machines(db: sqlite3.Connection) -> List[dict]:
    """Every host's newest snapshot as {machine, profile, state}, newest first: what snapshot.differences compares."""
    states = []
    for row in db.execute(NEWEST):
        last = json.loads(row['last_json'])
        states.append({'machine': last['machine'], 'profile': row['profile'], 'state': json.loads(row['state_json'])})
    return states


def git(workdir: Path, *args: str) -> str:
    """stdout of git in the bridge's bare repository; RuntimeError with git's last stderr line on failure."""
    done = subprocess.run(['git', '-C', str(workdir), *args], capture_output=True, text=True, timeout=GIT_TIMEOUT_S, check=False)
    if done.returncode:
        raise RuntimeError('git %s failed: %s' % (args[0], (done.stderr.strip().splitlines() or ['no output'])[-1]))
    return done.stdout


def read_ref(workdir: Path, ref: str) -> Tuple[dict, dict]:
    """(last, state) from a status branch; state is {} on branches pushed before snapshots existed."""
    last = json.loads(git(workdir, 'show', ref + ':last.json'))
    try:
        state = json.loads(git(workdir, 'show', ref + ':state.json'))
    except RuntimeError:
        state = {}
    return last, state


def bridge_once(db: sqlite3.Connection, remote: str, workdir: Path) -> int:
    """Fetch the remote's status/* branches and store each one newer than that host's stored report; how many were stored."""
    if not (workdir / 'HEAD').exists():
        workdir.mkdir(parents=True, exist_ok=True)
        git(workdir, 'init', '--bare', '--quiet')
    spec = '+refs/heads/%s*:refs/heads/%s*' % (sync.STATUS_REFS, sync.STATUS_REFS)
    git(workdir, 'fetch', '--quiet', '--force', '--prune', remote, spec)
    stored = 0
    for ref in git(workdir, 'for-each-ref', '--format=%(refname)', 'refs/heads/' + sync.STATUS_REFS).split():
        last, state = read_ref(workdir, ref)
        newest = db.execute('SELECT MAX(finished) FROM reports WHERE host = ?', (validate_last(last)[1],)).fetchone()[0]
        if newest is None or last['finished'] > newest:
            store_report(db, last, state)
            stored += 1
    return stored


def bridge_loop(config: HubConfig, remote: str, interval_s: int) -> None:
    """bridge_once forever; a failed pass (GitHub unreachable) is logged and retried next interval."""
    workdir = Path.home() / BRIDGE_DIR
    while True:
        try:
            with closing(connect(config.db)) as db:
                bridge_once(db, remote, workdir)
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, sqlite3.Error) as exc:
            print('bridge: %s' % exc, file=sys.stderr, flush=True)
        time.sleep(interval_s)


def strip_prefix(path: str) -> str:
    """'/converge/fleet' -> '/fleet', so the handler serves the same paths behind `tailscale serve --set-path`."""
    if path == PREFIX or path.startswith(PREFIX + '/'):
        path = path[len(PREFIX):]
    return path or '/'


def render_fleet(rows: List[dict]) -> str:
    """Minimal fleet page: the CLI's table in a <pre> (phase 3 adds drift and pending recipes)."""
    table = html.escape('\n'.join(sync.fleet_lines(rows)) or 'no check-ins yet')
    return ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>converge fleet</title><h1>converge fleet</h1><pre>%s</pre>\n' % table)


def parse_report(headers, stream) -> Tuple[dict, dict]:
    """(last, state) from a POST /report body; ValueError for an oversized body, a wrong type or bad JSON.
    The body is read before any other check: unread bytes make the close a reset that can eat the reply."""
    length = max(0, int(headers.get('Content-Length') or 0))
    if length > MAX_BODY:
        raise ValueError('body over %d bytes' % MAX_BODY)
    data = stream.read(length)
    if not headers.get('Content-Type', '').startswith(JSON):
        raise ValueError('Content-Type must be application/json')
    body = json.loads(data or b'null')
    if not isinstance(body, dict) or not isinstance(body.get('state', {}), dict):
        raise ValueError('body must be {"last": {...}, "state": {...}}')
    return body.get('last') or {}, body.get('state') or {}


def get(db: sqlite3.Connection, path: str) -> Reply:
    """Answer a GET: the fleet page, /fleet, /machines or /machine/<host>."""
    if path == '/':
        return Reply(200, render_fleet(fleet_rows(db)), PAGE)
    if path == '/fleet':
        return Reply(200, json.dumps(fleet_rows(db)), JSON)
    if path == '/machines':
        return Reply(200, json.dumps(machines(db)), JSON)
    if path.startswith('/machine/'):
        found = machine(db, unquote(path[len('/machine/'):]))
        return Reply(200, json.dumps(found), JSON) if found else Reply(404, 'no such host\n', TEXT)
    return Reply(404, 'not found\n', TEXT)


class Handler(BaseHTTPRequestHandler):
    """Routes requests to get() and the report store; self.server.config is a HubConfig."""

    def do_GET(self) -> None:
        self._answer(get)

    def do_POST(self) -> None:
        self._answer(self._post)

    def _post(self, db: sqlite3.Connection, path: str) -> Reply:
        """POST /report: 204 stored, 400 malformed, 403 not through tailscale serve (unless --trust-local)."""
        if path != '/report':
            return Reply(404, 'not found\n', TEXT)
        try:
            last, state = parse_report(self.headers, self.rfile)
            if not (self.headers.get('Tailscale-User-Login') or self.server.config.trust_local):
                return Reply(403, 'check-ins come through tailscale serve\n', TEXT)
            store_report(db, last, state)
        except ValueError as exc:
            return Reply(400, '%s\n' % str(exc).splitlines()[0], TEXT)
        return Reply(204, '', TEXT)

    def _answer(self, route) -> None:
        """Run a route on a fresh connection and send its reply; an unexpected error is one line to the client, a trace to the log."""
        try:
            with closing(connect(self.server.config.db)) as db:
                reply = route(db, strip_prefix(urlsplit(self.path).path))
        except Exception:  # noqa: BLE001 - never a stack trace to the client
            traceback.print_exc()
            reply = Reply(500, 'internal error\n', TEXT)
        body = reply.body.encode()
        self.send_response(reply.status)
        self.send_header('Content-Type', reply.kind)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - the base class's name
        """Access lines are noise in the journal; errors still print through log_error."""


def make_server(port: int, config: HubConfig) -> ThreadingHTTPServer:
    """Hub HTTP server on 127.0.0.1 (tailscale serve is the only way in from the tailnet); port 0 picks a free one."""
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.config = config
    return server


def serve(args: argparse.Namespace) -> int:
    """Run the hub until killed, with the bridge thread unless --bridge none."""
    config = HubConfig(Path(args.db), args.trust_local)
    connect(config.db).close()  # create the schema before the first request
    server = make_server(args.port, config)
    if args.bridge != 'none':
        threading.Thread(target=bridge_loop, args=(config, args.bridge, args.bridge_interval), daemon=True).start()
    print('converge hub on http://127.0.0.1:%d (db %s, bridge %s)' % (server.server_address[1], config.db, args.bridge), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def parser() -> argparse.ArgumentParser:
    """`hub.py serve` and `hub.py bridge-once`; CONVERGE_HUB_DB and CONVERGE_BRIDGE_REMOTE set the defaults."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--db', default=os.environ.get('CONVERGE_HUB_DB') or str(Path.home() / DB), help='sqlite database')
    common.add_argument('--bridge', default=os.environ.get('CONVERGE_BRIDGE_REMOTE') or REMOTE,
                        help='git remote whose status/* branches are imported, or none')
    p = argparse.ArgumentParser(prog='hub.py', description=__doc__.splitlines()[0])
    commands = p.add_subparsers(dest='command', metavar='command', required=True)
    run = commands.add_parser('serve', parents=[common], help='Serve check-ins and the fleet view on 127.0.0.1')
    run.add_argument('--port', type=int, default=PORT, help='0 picks a free port (printed on start)')
    run.add_argument('--bridge-interval', type=int, default=BRIDGE_INTERVAL_S, metavar='SECONDS')
    run.add_argument('--trust-local', action='store_true', help='Accept check-ins without the Tailscale-User-Login header (tests)')
    commands.add_parser('bridge-once', parents=[common], help='One bridge pass: import newer status/* branches, then exit')
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Run a hub subcommand; returns the exit code."""
    args = parser().parse_args(argv)
    if args.command == 'serve':
        return serve(args)
    with closing(connect(Path(args.db))) as db:
        print('%d reports stored' % bridge_once(db, args.bridge, Path.home() / BRIDGE_DIR))
    return 0


if __name__ == '__main__':
    sys.exit(main())
