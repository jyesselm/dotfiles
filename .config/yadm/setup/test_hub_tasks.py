"""converge hub -> Tasks hook: the pure helpers, and the sync against a fake Tasks server on an ephemeral 127.0.0.1 port."""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import hub
import hub_tasks as ht
import sync as sy
from test_hub import GH, report

TITLE = '🖥 book · Sign in to GitHub CLI'


class FakeTasks(BaseHTTPRequestHandler):
    """The routes the hook uses, behaving as server/app.py does: /done ticks one chain step, the last completes the task."""

    def do_GET(self) -> None:
        store = self.server.store
        if self.path == '/api/state':
            return self.reply({'projects': store['projects'], 'tasks': [decorate(t) for t in store['tasks'] if not t['completed_at']]})
        if self.path == '/api/projects':
            return self.reply(store['projects'])
        return self.reply({'detail': 'not found'}, 404)

    def do_POST(self) -> None:
        store, body = self.server.store, json.loads(self.rfile.read(int(self.headers['Content-Length'])) or b'{}')
        if self.path == '/api/projects':
            store['projects'].append(dict(body, id=len(store['projects']) + 1, archived=0))
            return self.reply(store['projects'][-1])
        if self.path == '/api/tasks':
            store['tasks'].append(dict(body, id=len(store['tasks']) + 1, completed_at=None))
            return self.reply(store['tasks'][-1])
        task = store['tasks'][int(self.path.split('/')[3]) - 1]  # /api/tasks/<id>/done
        step = decorate(task)['cur']
        if step >= 0:
            task['chain'][step]['done'] = True
        if decorate(task)['cur'] < 0:
            task['completed_at'] = 'now'
        return self.reply(task)

    def reply(self, data, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # noqa: A002
        """Quiet."""


def decorate(task: dict) -> dict:
    """A task with `cur`, the first step not done (-1 for a plain task or a finished chain), as /api/state adds it."""
    steps = [i for i, step in enumerate(task.get('chain') or []) if not step['done']]
    return dict(task, cur=steps[0] if steps else -1)


class HelperTests(unittest.TestCase):
    def test_task_title(self):
        self.assertEqual(ht.task_title('book', GH), TITLE)

    def test_step_titles_are_six_words_cut_sensibly(self):
        cases = {'gh auth login --hostname github.com --web': 'gh auth login',
                 'atuin login (username, password and encryption key are in 1Password)': 'atuin login',
                 'Pick SSH, choose ~/.ssh/id_ed25519.pub, finish in the browser': 'Pick SSH',
                 'System Settings > General > Login Items & Extensions': 'System Settings > General > Login',
                 'Open Karabiner-Elements once and allow its system extension': 'Open Karabiner-Elements once and allow',
                 'Mac: Tailscale menu-bar icon > "Log in..." (or "Connect")': 'Mac: Tailscale menu-bar icon',
                 'Add the ones wanted on every Mac to a Brewfile': 'Add the ones wanted',
                 'converge sync': 'converge sync'}
        for step, title in cases.items():
            self.assertEqual(ht.step_title(step), title)

    def test_chain_steps_keep_the_full_line_as_the_note(self):
        self.assertEqual(ht.chain_steps(['converge sync']), [{'title': 'converge sync', 'done': False, 'due': None, 'wait': False,
                                                             'note': 'converge sync'}])

    def test_plan_sync(self):
        stale = {'id': 2, 'title': '🖥 book · Old'}
        kept = {'id': 1, 'title': TITLE}
        self.assertEqual(ht.plan_sync([TITLE, '🖥 book · New'], [kept, stale]), (['🖥 book · New'], [stale]))
        self.assertEqual(ht.plan_sync([], []), ([], []))


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tasks = ThreadingHTTPServer(('127.0.0.1', 0), FakeTasks)
        self.tasks.store = {'projects': [{'id': 1, 'name': 'Inbox', 'archived': 0}], 'tasks': []}
        self.base = 'http://127.0.0.1:%d' % self.tasks.server_address[1]
        threading.Thread(target=self.tasks.serve_forever, daemon=True).start()
        self.addCleanup(self.tasks.server_close)
        self.addCleanup(self.tasks.shutdown)

    def open_titles(self):
        return [t['title'] for t in self.tasks.store['tasks'] if not t['completed_at']]

    def test_create_once_then_done_when_the_recipe_clears(self):
        self.assertEqual(ht.sync_host(self.base, 'book', [GH]), (1, 0))
        task = self.tasks.store['tasks'][0]
        self.assertEqual((task['title'], task['priority'], task['project_id']), (TITLE, 3, 2))
        self.assertEqual([s['title'] for s in task['chain']], ['gh auth login', 'converge sync'])
        self.assertEqual(self.tasks.store['projects'][-1]['name'], 'Computers')
        self.assertEqual(ht.sync_host(self.base, 'book', [GH]), (0, 0))  # no duplicate
        self.assertEqual(ht.sync_host(self.base, 'other', []), (0, 0))  # another host's report leaves it alone
        self.assertEqual(ht.sync_host(self.base, 'book', []), (0, 1))
        self.assertEqual(self.open_titles(), [])
        self.assertTrue(all(step['done'] for step in task['chain']))
        self.assertEqual(len(self.tasks.store['projects']), 2)  # Computers made once

    def test_unreachable_tasks_server_is_logged_not_raised(self):
        with patch('sys.stderr') as err:
            ht.guarded_sync('http://127.0.0.1:1', 'book', [GH])
        self.assertIn('tasks: book:', ''.join(c.args[0] for c in err.write.call_args_list))
        self.assertIsNone(ht.file_in_background(None, report('mac@book', pending=[GH])))

    def test_hub_files_tasks_after_a_check_in(self):
        with tempfile.TemporaryDirectory() as temp:
            server = hub.make_server(0, hub.HubConfig(Path(temp) / 'hub.sqlite', trust_local=True, tasks=self.base))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with patch.dict(os.environ, {'CONVERGE_HUB': 'http://127.0.0.1:%d' % server.server_address[1]}):
                    sy.request('/report', {'last': report('laptop@book', pending=[GH]), 'state': {}})
                    self.assertTrue(self.wait_for([TITLE]))
                    sy.request('/report', {'last': report('laptop@book'), 'state': {}})
                    self.assertTrue(self.wait_for([]))
            finally:
                server.shutdown()
                server.server_close()

    def wait_for(self, titles, timeout_s: float = 5) -> bool:
        """Whether the open task titles become `titles` within the timeout (the hook runs in a background thread)."""
        end = time.time() + timeout_s
        while time.time() < end:
            if self.open_titles() == titles and len(self.tasks.store['tasks']) == 1:
                return True
            time.sleep(0.05)
        return False


if __name__ == '__main__':
    unittest.main()
