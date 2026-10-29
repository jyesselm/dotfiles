"""Effective-state snapshot and the cross-machine diff, with no real commands."""
import importlib.util
import io
import contextlib
import json
import plistlib
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

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


class LoginTests(Base):
    def test_gh_op_and_tailscale_logins(self):
        self.calls['gh auth status'] = done('', 0, 'github.com\n  Logged in to github.com account jyesselm (keyring)\n')
        (self.root / sn.OP_CLI_CONFIG).parent.mkdir(parents=True)
        (self.root / sn.OP_CLI_CONFIG).write_text('{"accounts": [{"url": "x", "email": "a@b.org"}]}')
        self.calls['tailscale status --json'] = done('{"BackendState": "Running", "Self": {"Online": true}}')
        setup = self.setup('--profile', 'linux', tools=('gh', 'op', 'tailscale'))
        self.assertEqual((sn.gh_login(setup), sn.op_account(setup), sn.tailscale_online(setup)), ('jyesselm', 'a@b.org', 'yes'))
        self.calls['gh auth status'] = done('', 0, 'Logged in to github.com as old (oauth_token)\n')
        self.calls['tailscale status --json'] = done('{"BackendState": "Stopped"}', 1)
        (self.root / sn.OP_CLI_CONFIG).write_text('{"accounts": null}')
        self.assertEqual((sn.gh_login(setup), sn.op_account(setup), sn.tailscale_online(setup)), ('old', 'none', 'no'))
        self.calls['gh auth status'] = done('', 1, 'You are not logged into any GitHub hosts')
        self.calls['tailscale status --json'] = done('not json')
        self.assertEqual((sn.gh_login(setup), sn.tailscale_online(setup)), ('not logged in', 'no'))
        bare = self.setup('--profile', 'linux', tools=())
        self.assertEqual((sn.gh_login(bare), sn.op_account(bare), sn.tailscale_online(bare)), ('gh missing', 'none', 'absent'))
        mac = self.setup('--profile', 'mac', tools=())
        self.assertEqual(sn.op_account(mac), 'none')
        settings = self.root / sn.OP_APP_SETTINGS
        settings.parent.mkdir(parents=True)
        settings.write_text('{"developers.cliSharedLockState.enabled": true}')
        self.assertEqual(sn.op_account(mac), 'app')

    def test_atuin_age_keys_and_keychain_secrets(self):
        self.assertEqual(sn.atuin_synced(self.root), 'absent')
        path = self.root / sn.ATUIN_SYNC
        path.parent.mkdir(parents=True)
        path.write_text((datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%S.12345Z'))
        self.assertEqual(sn.atuin_synced(self.root), 5.0)
        path.write_text('garbage')  # falls back to the file's mtime: just written
        self.assertEqual(sn.atuin_synced(self.root), 0.0)
        self.assertEqual(sn.iso_time('2026-10-28T12:00:00.123456789+00:00').microsecond, 123456)
        (self.root / '.ssh').mkdir()
        (self.root / '.ssh/id_ecdsa.pub').write_text('')
        self.assertEqual(sn.own_keys(self.root), ['id_ecdsa.pub'])
        setup = self.setup('--profile', 'mac')
        self.assertEqual(sn.secrets_missing(setup), 'absent')
        (self.root / sn.SECRETS_REFS).parent.mkdir(parents=True)
        (self.root / sn.SECRETS_REFS).write_text('# refs\nHAVE  op://Vault/item/field\nLACK  op://Vault/other/field\n')
        self.calls['security find-generic-password -s zsh-keys -a HAVE'] = done('keychain: x')
        self.assertEqual(sn.secrets_missing(setup), ['LACK'])

    def test_linux_inventories_and_declared_keys(self):
        assets = self.root / 'assets'
        (assets / 'declared').mkdir(parents=True)
        (assets / 'declared/apt.txt').write_text('git\nvim\n')
        setup = m.Setup(m.parse(['sync', '--profile', 'linux']), root=self.root, assets=assets)
        setup.find = lambda name: '/bin/' + name if name in ('apt-mark', 'snap') else None
        setup.read = lambda argv, **kw: self.calls.get(' '.join(map(str, argv)), done('', 1, 'not stubbed'))
        self.calls.update({'apt-mark showmanual': done('git\nzsh\n'), 'snap list': done('Name Version Rev\ncode 1.95 9\n'),
                           'dpkg-query -W -f ${Package} ${Version}\n git zsh': done('git 1:2.43\nzsh 5.9\n')})
        with patch.object(sn, '_module', return_value=m):  # the temp assets dir has no setup.py
            state = sn.collect(setup)
        self.assertEqual((state['apt.git'], state['apt.zsh'], state['snap.code']), ('1:2.43', '5.9', '1.95'))
        self.assertNotIn('flatpak.x', state)
        self.assertEqual((state['declared.apt.missing'], state['declared.apt.undeclared']), (['vim'], ['zsh']))
        self.assertEqual(state['declared.flatpak.missing'], [])


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
                    {'machine': 'studio@desk', 'profile': 'mac', 'state': {'os': 'mac 26', 'tools.git': '2.5', 'fonts': ['a'], 'apps.Tasks': '1'}},
                    {'machine': 'server@plex', 'profile': 'mac', 'state': {'os': 'mac 26', 'tools.git': '2.5'}},  # no apps group: left out of apps rows
                    {'machine': 'linux@gpu', 'profile': 'linux', 'state': {'os': 'linux 6', 'tools.git': '2.4'}},
                    {'machine': 'cluster@swan', 'profile': 'cluster', 'state': {}}]
        rules = {'compare': ['*'], 'ignore': ['fonts']}
        rows = sn.differences(statuses, rules)
        self.assertEqual(rows, [('apps.CleanShot X', {'book': '4.7', 'desk': '-'}),  # Macs with apps only: linux and the server have none
                                ('apps.Tasks', {'book': '-', 'desk': '1'}),
                                ('os', {'book': 'mac 26', 'desk': 'mac 26', 'plex': 'mac 26', 'gpu': 'linux 6'}),
                                ('tools.git', {'book': '2.5', 'desk': '2.5', 'plex': '2.5', 'gpu': '2.4'})])
        self.assertEqual([k for k, _ in sn.differences(statuses, sn.EVERY_KEY)], ['apps.CleanShot X', 'apps.Tasks', 'fonts', 'os', 'tools.git'])
        lines = sn.table(rows, ['book', 'desk', 'gpu'])
        self.assertEqual(lines[0], 'key               book    desk    gpu')
        self.assertEqual(lines[1], 'apps.CleanShot X  4.7     -')
        self.assertEqual(sn.table([], ['book']), [])
        fonts = sn.table([('fonts', {'book': ['a', 'b'], 'desk': ['a', 'c'], 'gpu': 'x'})], ['book', 'desk', 'gpu'])
        self.assertEqual(fonts[1], 'fonts  lacks: c  lacks: b  x')
        self.assertEqual(sn.show(['a'], [['a']]), 'has all')
        self.assertEqual(sn.show('x' * 60), 'x' * 49 + '…')

    def test_fleet_diff_prints_table_and_keys_lists_own_state(self):
        setup = self.setup()
        setup.args = m.parse(['fleet', '--diff'])
        fleet = self.root / 'fleet.txt'
        fleet.write_text('laptop\n')
        (self.root / 'compare.yml').write_text('compare:\n  - tools.*\n')
        setup.assets = self.root
        rows, states = [], []
        for host, git in [('book', '2.5'), ('desk', '2.4')]:
            rows.append({'host': host, 'class': 'x', 'finished': '2026-10-17T12:00:00+00:00', 'exit': 0, 'phases': {}, 'corrective': 0, 'stale': False})
            states.append({'machine': 'x@' + host, 'profile': 'mac', 'state': {'tools.git': git, 'os': host}})
        answers = {'/fleet': rows, '/machines': states}
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(sy, 'request', lambda path, body=None: json.dumps(answers[path]).encode()):
            sy.fleet(setup, fleet)
            setup.args = m.parse(['fleet', '--diff', '--all'])
            sy.fleet(setup, fleet)
        text = out.getvalue()
        self.assertIn('1 differences in 2 compared keys (setup/compare.yml)', text)
        self.assertIn('tools.git  2.5   2.4', text)
        self.assertNotIn('os ', text.split('key')[1].split('differences')[0])
        self.assertIn('2 differences in 4 compared keys (everything)', text)
        setup.args = m.parse(['fleet', '--keys'])
        (self.root / sy.STATE_DIR).mkdir(parents=True)
        (self.root / sy.STATE_DIR / 'state.json').write_text(json.dumps({'fonts': ['a', 'b'], 'os': 'mac'}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sy.fleet(setup, fleet), 0)
        self.assertIn('fonts                                    a, b', out.getvalue())
        self.assertIn('2 keys', out.getvalue())


if __name__ == '__main__':
    unittest.main()
