"""Effective-state snapshot and the cross-machine diff, with no real commands."""
import importlib.util
import io
import contextlib
import json
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

import snapshot as sn
import sync as sy

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def done(out='', code=0, err=''):
    return subprocess.CompletedProcess([], code, out, err)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()
        self.calls = {}  # 'git config user.email' -> CompletedProcess

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def setup(self, *argv, tools=('git',)):
        setup = m.Setup(m.parse(['sync', *argv]), root=self.root)
        setup.find = lambda name: '/bin/' + name if name in tools else None
        setup.read = lambda argv, **kw: self.calls.get(' '.join(Path(a).name if i == 0 else str(a) for i, a in enumerate(argv)), done('', 1, 'not stubbed'))
        return setup


class CollectTests(Base):
    def test_linux_snapshot_has_tools_checkouts_and_errors_per_key(self):
        setup = self.setup('--profile', 'linux', tools=('git', 'tmux', 'uv'))
        self.calls.update({'git config user.email': done('joe@x.org\n'), 'tmux -V': done('tmux 3.6a\n'),
                           'uv tool list': done('git-repo-checker v0.1.0\n- grc\nsearch-cli v0.2.0\n')})
        checkout = self.root / m.DEVELOPING / 'git-repo-checker'
        (checkout / '.git').mkdir(parents=True)
        self.calls['git -C %s rev-parse --short HEAD' % checkout] = done('abc123\n')
        self.calls['git -C %s status --porcelain' % checkout] = done(' M x.py\n')
        (self.root / '.ssh').mkdir()
        (self.root / '.ssh/id_ed25519.pub').write_text('')
        state = sn.collect(setup)
        self.assertEqual(state['git.email'], 'joe@x.org')
        self.assertEqual(state['tools.tmux'], '3.6')
        self.assertEqual(state['tools.nvim'], 'missing')
        self.assertEqual(state['uv.search-cli'], '0.2.0')
        self.assertEqual(state['checkouts.git-repo-checker'], 'abc123+dirty')
        self.assertEqual(state['ssh.keys'], ['id_ed25519.pub'])
        self.assertEqual(state['gh.auth'], 'gh missing')
        self.assertNotIn('apps', ' '.join(state))

    def test_mac_gatherers_shortcuts_and_apps(self):
        plist = plistlib.dumps({'AppleSymbolicHotKeys': {'31': {'enabled': True, 'value': {'parameters': [52, 21, 1441792]}},
                                                         '28': {'enabled': False}, '999': {'enabled': True}}})
        flags = sn.shortcut_flags(plist)
        self.assertEqual(flags, {'shortcuts.31 area-clipboard': 'on 52 21 1441792', 'shortcuts.28 screenshot-file': 'off', 'shortcuts.999': 'on'})
        apps = self.root / 'Applications'
        (apps / 'Tasks.app/Contents').mkdir(parents=True)
        (apps / 'Tasks.app/Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleShortVersionString': '0.2.1'}))
        (apps / 'Broken.app').mkdir()
        (apps / '.Helper.app').mkdir()
        self.assertEqual(sn.app_versions([apps, self.root / 'none']), {'apps.Tasks': '0.2.1', 'apps.Broken': '?'})
        self.assertEqual(sn.active_repos(self.root / 'missing.yml'), [])
        (self.root / 'a.yml').write_text("path_prefix: '~'\nrepos:\n- path: local/code/x\n  remote: r\n- path: 'local/code/y'\n")
        self.assertEqual(sn.active_repos(self.root / 'a.yml'), ['local/code/x', 'local/code/y'])


class CompareTests(Base):
    def test_compare_yml_subset_and_selection(self):
        path = self.root / 'compare.yml'
        path.write_text('# header\ncompare:\n  - os\n  - apps.*   # all apps\nignore:\n  - "apps.Xcode"\n')
        rules = sn.load_compare(path)
        self.assertEqual(rules, {'compare': ['os', 'apps.*'], 'ignore': ['apps.Xcode']})
        self.assertTrue(sn.selected('apps.Tasks', rules))
        self.assertFalse(sn.selected('apps.Xcode', rules))
        self.assertFalse(sn.selected('tools.git', rules))
        self.assertEqual(sn.load_compare(self.root / 'absent.yml'), {'compare': [], 'ignore': []})
        path.write_text('compare:\n  os\n')
        with self.assertRaises(ValueError):
            sn.load_compare(path)

    def test_differences_compare_within_profiles_and_table_aligns(self):
        statuses = [{'machine': 'laptop@book', 'profile': 'mac', 'state': {'os': 'mac 26', 'apps.CleanShot X': '4.7', 'tools.git': '2.5', 'fonts': ['a', 'b']}},
                    {'machine': 'studio@desk', 'profile': 'mac', 'state': {'os': 'mac 26', 'tools.git': '2.5', 'fonts': ['a']}},
                    {'machine': 'linux@gpu', 'profile': 'linux', 'state': {'os': 'linux 6', 'tools.git': '2.4'}},
                    {'machine': 'cluster@swan', 'profile': 'cluster', 'state': {}}]
        rules = {'compare': ['*'], 'ignore': ['fonts']}
        rows = sn.differences(statuses, rules)
        self.assertEqual(rows, [('apps.CleanShot X', {'book': '4.7', 'desk': '-'}),  # Macs only: linux never has apps
                                ('os', {'book': 'mac 26', 'desk': 'mac 26', 'gpu': 'linux 6'}),
                                ('tools.git', {'book': '2.5', 'desk': '2.5', 'gpu': '2.4'})])
        self.assertEqual([k for k, _ in sn.differences(statuses, rules, everything=True)], ['apps.CleanShot X', 'fonts', 'os', 'tools.git'])
        lines = sn.table(rows, ['book', 'desk', 'gpu'])
        self.assertEqual(lines[0], 'key               book    desk    gpu')
        self.assertEqual(lines[1], 'apps.CleanShot X  4.7     -')
        self.assertEqual(sn.table([], ['book']), [])
        fonts = sn.table([('fonts', {'book': ['a', 'b'], 'desk': ['a', 'c'], 'gpu': 'x'})], ['book', 'desk', 'gpu'])
        self.assertEqual(fonts[1], 'fonts  lacks: c  lacks: b  x')
        self.assertEqual(sn.show(['a'], [['a']]), 'has all')
        self.assertEqual(sn.show('x' * 60), 'x' * 49 + '…')

    def test_fleet_diff_prints_table_and_keys_lists_own_state(self):
        setup = self.setup(tools=('git', 'yadm'))
        fleet = self.root / 'fleet.txt'
        fleet.write_text('laptop\n')
        (self.root / 'compare.yml').write_text('compare:\n  - tools.*\n')
        setup.assets = self.root
        refs = ['refs/remotes/origin/status/laptop-book', 'refs/remotes/origin/status/studio-desk']
        self.calls['yadm fetch --quiet --prune origin +refs/heads/status/*:refs/remotes/origin/status/*'] = done()
        self.calls['yadm for-each-ref --format=%(refname) refs/remotes/origin/status/'] = done('\n'.join(refs) + '\n')
        for ref, host, git in zip(refs, ['book', 'desk'], ['2.5', '2.4']):
            data = {'machine': 'x@' + host, 'profile': 'mac', 'finished': '2026-10-17T12:00:00+00:00', 'exit': 0, 'phases': {}}
            self.calls['yadm show %s:last.json' % ref] = done(json.dumps(data))
            self.calls['yadm show %s:state.json' % ref] = done(json.dumps({'tools.git': git, 'os': host}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sy.fleet(setup, fleet, diff=True)
        text = out.getvalue()
        self.assertIn('1 differences in 2 compared keys (setup/compare.yml)', text)
        self.assertIn('tools.git  2.5   2.4', text)
        self.assertNotIn('os ', text.split('key')[1])
        (self.root / sy.STATE_DIR).mkdir(parents=True)
        (self.root / sy.STATE_DIR / 'state.json').write_text(json.dumps({'fonts': ['a', 'b'], 'os': 'mac'}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sy.fleet(setup, fleet, keys=True), 0)
        self.assertIn('fonts                                    a, b', out.getvalue())
        self.assertIn('2 keys', out.getvalue())


if __name__ == '__main__':
    unittest.main()
