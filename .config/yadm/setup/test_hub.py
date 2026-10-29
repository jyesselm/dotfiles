"""converge hub: report store, git bridge and HTTP routes on a temp database; HTTP only on an ephemeral 127.0.0.1 port."""
import http.client
import json
import os
import subprocess
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import hub
import sync as sy

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')


def git_out(repo: Path, *args: str, given: Optional[str] = None) -> str:
    """stdout of git in `repo`, with `given` on stdin."""
    return subprocess.run(['git', '-C', str(repo), *args], input=given, capture_output=True, text=True, check=True, env=GIT_ENV).stdout.strip()


def last(machine, hours_ago=1, exit_code=0, phases=None):
    """A minimal last.json."""
    finished = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    phases = phases or {'layout': 'ok'}
    return {'machine': machine, 'profile': 'linux', 'finished': finished, 'exit': exit_code,
            'phases': {k: {'status': v, 'summary': '', 'details': []} for k, v in phases.items()}}


class Temp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.db = hub.connect(self.dir / 'hub.sqlite')
        self.addCleanup(self.db.close)


class StoreTests(Temp):
    def test_fleet_rows_are_newest_per_host_newest_first(self):
        hub.store_report(self.db, last('mac@studio', 90), {})
        hub.store_report(self.db, last('studio@studio', 60, 1, {'dotfiles': 'failed', 'keys': 'changed'}), {'os': 'a'})
        hub.store_report(self.db, last('laptop@book', 2), {'os': 'b'})
        rows = hub.fleet_rows(self.db)
        self.assertEqual([(r['host'], r['class']) for r in rows], [('book', 'laptop'), ('studio', 'studio')])
        self.assertEqual(rows[1]['phases'], {'dotfiles': 'failed', 'keys': 'changed'})
        self.assertEqual((rows[1]['exit'], rows[1]['corrective'], rows[1]['stale']), (1, 1, True))
        self.assertFalse(rows[0]['stale'])
        self.assertEqual(sy.fleet_lines(rows)[-1], 'stale: studio@studio last checked in 2d ago')

    def test_machine_and_machines_return_the_newest_snapshot(self):
        hub.store_report(self.db, last('laptop@book', 5), {'os': 'old'})
        hub.store_report(self.db, last('laptop@book', 1), {'os': 'new'})
        self.assertEqual(hub.machine(self.db, 'book')['state'], {'os': 'new'})
        self.assertIsNone(hub.machine(self.db, 'nobody'))
        self.assertEqual(hub.machines(self.db), [{'machine': 'laptop@book', 'profile': 'linux', 'state': {'os': 'new'}}])

    def test_prune_drops_reports_received_long_ago(self):
        hub.store_report(self.db, last('laptop@book'), {})
        old = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
        with self.db:
            self.db.execute('UPDATE reports SET received = ?', (old,))
        hub.store_report(self.db, last('laptop@book'), {})  # every insert prunes
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM reports').fetchone()[0], 1)
        self.assertEqual(hub.prune(self.db, 0), 1)

    def test_store_rejects_what_is_not_a_last_json(self):
        for bad in [{}, {'machine': 'nohost', 'phases': {}, 'finished': '2026-01-01'}, dict(last('a@b'), phases=[]),
                    dict(last('a@b'), finished='yesterday')]:
            with self.assertRaises(ValueError):
                hub.store_report(self.db, bad, {})

    def test_strip_prefix(self):
        self.assertEqual([hub.strip_prefix(p) for p in ['/converge/fleet', '/converge', '/fleet', '/convergex', '']],
                         ['/fleet', '/', '/fleet', '/convergex', '/'])


class BridgeTests(Temp):
    def push_status(self, remote, data, state=None):
        """Point status/<class>-<host> at a parentless commit of last.json (and state.json), as publish_status makes it."""
        files = {'last.json': data} if state is None else {'last.json': data, 'state.json': state}
        blobs = {name: git_out(remote, 'hash-object', '-w', '--stdin', given=json.dumps(value)) for name, value in files.items()}
        entries = ''.join('100644 blob %s\t%s\n' % (blob, name) for name, blob in blobs.items())
        commit = git_out(remote, 'commit-tree', git_out(remote, 'mktree', given=entries), '-m', 'status')
        git_out(remote, 'update-ref', 'refs/heads/' + sy.status_ref(data['machine']), commit)

    def test_bridge_stores_status_branches_once_and_again_when_newer(self):
        remote = self.dir / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '--quiet', str(remote)], check=True)
        self.push_status(remote, last('cluster@login.swan', 3), {'os': 'linux'})
        self.push_status(remote, last('linux@old'))  # pushed before snapshots existed: no state.json
        workdir = self.dir / 'bridge'
        self.assertEqual(hub.bridge_once(self.db, 'file://%s' % remote, workdir), 2)
        self.assertEqual(hub.bridge_once(self.db, 'file://%s' % remote, workdir), 0)
        self.assertEqual(hub.machine(self.db, 'login.swan')['state'], {'os': 'linux'})
        self.assertEqual(hub.machine(self.db, 'old')['state'], {})
        self.push_status(remote, last('cluster@login.swan', 1, 1), {'os': 'linux'})
        self.assertEqual(hub.bridge_once(self.db, 'file://%s' % remote, workdir), 1)
        self.assertEqual(hub.machine(self.db, 'login.swan')['last']['exit'], 1)

    def test_bridge_failure_names_git(self):
        with self.assertRaisesRegex(RuntimeError, 'git fetch failed'):
            hub.bridge_once(self.db, 'file://%s' % (self.dir / 'absent.git'), self.dir / 'bridge')


class HttpTests(Temp):
    def setUp(self):
        super().setUp()
        self.config = hub.HubConfig(self.dir / 'hub.sqlite', trust_local=True)
        self.server = hub.make_server(0, self.config)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def call(self, method, path, body=b'', headers=None):
        """(status, body text) of one raw request."""
        with closing(http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)) as conn:
            conn.request(method, path, body, headers or {})
            answer = conn.getresponse()
            return answer.status, answer.read().decode()

    def test_checkin_round_trip_through_the_client_functions(self):
        with patch.dict(os.environ, {'CONVERGE_HUB': 'http://127.0.0.1:%d/converge' % self.port}):
            sy.request('/report', {'last': last('laptop@book'), 'state': {'os': 'mac'}})
            rows = sy.fetch_fleet()
            states = sy.fetch_machines()
        self.assertEqual([(r['host'], r['exit'], r['phases']) for r in rows], [('book', 0, {'layout': 'ok'})])
        self.assertEqual(states[0]['state'], {'os': 'mac'})
        status, page = self.call('GET', '/converge/')
        self.assertEqual(status, 200)
        self.assertIn('<pre>book ', page)
        self.assertEqual(json.loads(self.call('GET', '/machine/book')[1])['state'], {'os': 'mac'})
        self.assertEqual(self.call('GET', '/machine/nobody')[0], 404)
        self.assertEqual(self.call('GET', '/elsewhere')[0], 404)

    def test_post_needs_the_tailscale_header_unless_trust_local(self):
        body = json.dumps({'last': last('laptop@book'), 'state': {}}).encode()
        self.config.trust_local = False
        self.assertEqual(self.call('POST', '/report', body, {'Content-Type': 'application/json'})[0], 403)
        tailnet = {'Content-Type': 'application/json', 'Tailscale-User-Login': 'joe@example.com'}
        self.assertEqual(self.call('POST', '/report', body, tailnet)[0], 204)

    def test_bad_reports_are_400_with_one_line(self):
        cases = [(b'{nope', {'Content-Type': 'application/json'}),
                 (b'{}', {'Content-Type': 'text/plain'}),
                 (b'{"last": {}}', {'Content-Type': 'application/json'}),
                 (b'', {'Content-Type': 'application/json', 'Content-Length': str(hub.MAX_BODY + 1)})]  # refused before reading
        for body, headers in cases:
            status, text = self.call('POST', '/report', body, headers)
            self.assertEqual(status, 400, text)
            self.assertEqual(len(text.splitlines()), 1)
        self.assertEqual(hub.fleet_rows(self.db), [])


if __name__ == '__main__':
    unittest.main()
