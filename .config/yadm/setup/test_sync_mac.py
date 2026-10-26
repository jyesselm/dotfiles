"""Brewfile logic and home-made app installs, with no real brew, gh or /Applications."""
import contextlib
import importlib.util
import io
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sync_mac as sm

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

APP = {'name': 'Tasks', 'bundle_id': 'com.x.tasks', 'repo': 'o/tasks', 'bundle': 'Tasks.app',
       'assets': {'arm64': 'Tasks-arm64.zip', 'x86_64': 'Tasks-x64.zip'}}


DOWNLOAD = dict(APP, asset='Tasks-arm64.zip')


def done(out='', code=0, err=''):
    return subprocess.CompletedProcess([], code, out, err)


def make_app(path, bundle_id, short):
    (path / 'Contents').mkdir(parents=True)
    (path / 'Contents/Info.plist').write_bytes(plistlib.dumps(
        {'CFBundleIdentifier': bundle_id, 'CFBundleShortVersionString': short}))


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def setup(self, *argv):
        return m.Setup(m.parse(list(argv)), root=self.root)


class PureHelperTests(unittest.TestCase):
    def test_merge_brewfiles_dedupes_and_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, 'A'), Path(tmp, 'B')
            a.write_text('# note\nbrew "git"\n')
            b.write_text('# note\nbrew "git"\ncask "x"\n')
            text = sm.merge_brewfiles([a, b])
        self.assertEqual(text.count('brew "git"'), 1)
        self.assertEqual(text.count('# note'), 2)
        self.assertIn('# --- B ---', text)

    def test_parse_brewfile_reads_brew_cask_mas_and_present_hints(self):
        manifest = sm.parse_brewfile('brew "git"\ncask "zoom"   # present: /Applications/zoom.us.app\n'
                                     'cask "slack"\nmas "Magnet", id: 441258766\n')
        self.assertEqual((manifest.formulae, manifest.casks, manifest.mas_ids), (['git'], ['zoom', 'slack'], [441258766]))
        self.assertEqual(manifest.present, {'zoom': '/Applications/zoom.us.app'})

    def test_extras_ignore_tap_prefix_and_version_suffix(self):
        manifest = sm.parse_brewfile('brew "python"\nbrew "jq"\ncask "slack"\n')
        extras = sm.brew_extras(['python@3.14', 'jq', 'homebrew/core/ripgrep'], ['slack', 'runelite'], manifest)
        self.assertEqual(extras, ['cask:runelite', 'formula:ripgrep'])
        self.assertEqual(sm.brew_extras(['ripgrep'], ['runelite'], manifest, {'cask:runelite'}), ['formula:ripgrep'])

    def test_parse_extras_normalizes_and_rejects_bare_names(self):
        self.assertEqual(sm.parse_extras('# why\nformula:wget  # keep\ncask:zed@preview\n\n'), {'formula:wget', 'cask:zed'})
        with self.assertRaises(ValueError):
            sm.parse_extras('wget\n')

    def test_present_outside_brew_uses_app_artifact_and_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            apps = Path(tmp)
            (apps / 'Slack.app').mkdir()
            hint = apps / 'tex'
            hint.mkdir()
            manifest = sm.parse_brewfile('cask "slack"\ncask "basictex"  # present: %s\ncask "spotify"\ncask "gone"\n' % hint)
            info = {'casks': [{'token': 'slack', 'artifacts': [{'app': ['Slack.app']}, {'zap': []}]},
                              {"token": "spotify", 'artifacts': [{'app': ['Spotify.app']}]}]}
            found = sm.present_outside_brew(manifest, ['spotify'], sm.cask_app_names(info), apps)
        self.assertEqual(found, ['slack', 'basictex'])


class PackagesTests(Base):
    def reads(self, argv):
        table = {'list': done('slack\n'), 'leaves': done('git\nwget\nnot-in-any-brewfile\n'),
                 'info': done(json.dumps({'casks': [{'token': 'zoom', 'artifacts': []}]}))}
        return table[argv[1]]

    def assets(self, extras=''):
        """A manifest directory with one Brewfile and an extras.txt."""
        assets = self.root / 'assets'
        assets.mkdir()
        (assets / 'Brewfile').write_text('brew "git"\ncask "zoom"\n')
        for name in sm.BREWFILES['laptop'][1:]:
            (assets / name).write_text('')
        (assets / sm.EXTRAS_FILE).write_text(extras)
        return assets

    def test_adopt_extras_appends_unlisted_extras_until_clean(self):
        assets = self.assets('formula:wget\n')
        setup = m.Setup(m.parse(['adopt-extras', '--profile', 'mac']), root=self.root, assets=assets)
        with patch.object(setup, 'read', side_effect=self.reads), patch.object(setup, 'find', return_value='brew'), \
                patch.object(setup, 'run'):
            self.assertEqual(sm.adopt_extras(setup, 'laptop', self.root), 0)
            text = (assets / sm.EXTRAS_FILE).read_text()
            self.assertEqual(text.splitlines()[2:], ['cask:slack', 'formula:not-in-any-brewfile'])
            self.assertTrue(text.splitlines()[1].startswith('# laptop, adopted '))
            self.assertEqual(sm.adopt_extras(setup, 'laptop', self.root), 0)
            self.assertEqual((assets / sm.EXTRAS_FILE).read_text(), text)
            result = sm.packages(setup, 'laptop', self.root)
        self.assertNotIn('warn', result.status)
        self.assertEqual([d for d in result.details if not d.startswith('present:')], [])

    def test_adopt_extras_plan_writes_nothing_and_needs_a_mac(self):
        assets = self.assets()
        setup = m.Setup(m.parse(['adopt-extras', '--plan', '--profile', 'mac']), root=self.root, assets=assets)
        with patch.object(setup, 'read', side_effect=self.reads), patch.object(setup, 'find', return_value='brew'):
            sm.adopt_extras(setup, 'laptop', self.root)
        self.assertEqual((assets / sm.EXTRAS_FILE).read_text(), '')
        with self.assertRaises(RuntimeError):
            sm.adopt_extras(self.setup('--adopt-extras', '--profile', 'linux'), 'linux', self.root)

    def test_packages_plan_prints_bundle_command_without_temp_file(self):
        setup = self.setup('--plan', '--profile', 'mac')
        with patch.object(setup, 'read', side_effect=self.reads), patch.object(setup, 'find', return_value='brew'), \
                patch.object(m.subprocess, 'run', side_effect=AssertionError('ran')), \
                patch.object(sm.tempfile, 'TemporaryDirectory', side_effect=AssertionError('temp file')):
            result = sm.packages(setup, 'laptop', self.root)
        self.assertEqual(result.status, 'warn')
        self.assertIn('extras', result.summary)
        self.assertIn('formula:not-in-any-brewfile', result.details)

    def test_packages_real_passes_cask_skip_env_and_devnull_stdin(self):
        setup = self.setup('--profile', 'mac')
        (self.root / 'Zoom.app').mkdir()
        info = done(json.dumps({'casks': [{'token': 'zoom', 'artifacts': [{'app': ['Zoom.app']}]}]}))
        with patch.object(setup, 'read', side_effect=lambda a: info if a[1] == 'info' else done('slack\n')), \
                patch.object(setup, 'find', return_value='brew'), patch.object(setup, 'run') as run:
            result = sm.packages(setup, 'laptop', self.root)
        kwargs = run.call_args.kwargs
        self.assertIn('zoom', kwargs['env']['HOMEBREW_BUNDLE_CASK_SKIP'].split())
        self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
        self.assertIn('present:zoom', result.details)
        self.assertEqual(kwargs['timeout'], sm.BREW_TIMEOUT)

    def test_unknown_class_uses_terminal_brewfile_and_warns(self):
        setup = self.setup('--plan', '--profile', 'mac')
        with patch.object(setup, 'read', side_effect=self.reads), patch.object(setup, 'find', return_value='brew'):
            result = sm.packages(setup, 'mac', self.root)
        self.assertEqual(result.status, 'warn')
        self.assertIn('1 Brewfiles', result.summary)
        self.assertEqual(result.status, 'warn')


class AppTests(Base):
    def test_needs_upgrade(self):
        self.assertTrue(sm.needs_upgrade('0.2.0', 'v0.2.1'))
        self.assertFalse(sm.needs_upgrade('0.2.1', 'v0.2.1'))
        self.assertTrue(sm.needs_upgrade(None, 'v0.1.0'))
        self.assertFalse(sm.needs_upgrade('0.3.0', 'v0.2.1'))

    def test_installed_version_rejects_foreign_bundle_id(self):
        make_app(self.root / 'Tasks.app', 'com.other.app', '9.9')
        with self.assertRaises(RuntimeError):
            sm.installed_version(self.root / 'Tasks.app', 'com.x.tasks')
        self.assertIsNone(sm.installed_version(self.root / 'Missing.app', 'com.x.tasks'))

    def test_no_release_app_reports_build_hint(self):
        app = dict(APP, name='Hotkeys', bundle='Hotkeys.app', assets={}, build='npm run install-app')
        make_app(self.root / 'Hotkeys.app', 'com.x.tasks', '0.1.0')
        detail, state = sm.sync_app(self.setup('--profile', 'mac'), app, self.root, 'arm64')
        self.assertIn('build locally: npm run install-app', detail)
        self.assertEqual(state, 'warn')

    def test_checkout_app_is_built_when_its_commit_changes(self):
        setup = self.setup('--profile', 'mac')
        app = dict(APP, name='Hotkeys', bundle='Hotkeys.app', assets={}, checkout='local/code/web/hotkeys',
                   build='npm install && npm run install-app')
        detail, state = sm.sync_app(setup, app, self.root, 'arm64')
        self.assertEqual((state, detail), ('warn', 'Hotkeys absent: checkout ~/local/code/web/hotkeys absent (grc clones it); not built'))
        checkout = self.root / 'local/code/web/hotkeys'
        (checkout / '.git').mkdir(parents=True)
        reads = {'git': done('abcdef0123\n'), 'pgrep': done('', 1)}
        runs = []
        with patch.object(setup, 'read', side_effect=lambda a: reads[a[0]]), patch.object(setup, 'run', side_effect=lambda a, **k: runs.append((a, k))):
            detail, state = sm.sync_app(setup, app, self.root, 'arm64')
            self.assertEqual((state, detail), ('changed', 'Hotkeys absent -> abcdef0 built'))
            self.assertEqual(runs[0][0], ['sh', '-c', 'npm install && npm run install-app'])
            self.assertEqual(runs[0][1]['cwd'], checkout)
            make_app(self.root / 'Hotkeys.app', 'com.x.tasks', '0.1.0')
            self.assertEqual(sm.sync_app(setup, app, self.root, 'arm64'), ('Hotkeys 0.1.0 up to date (built from abcdef0)', 'ok'))
            reads['git'] = done('1234567aaa\n')
            reads['pgrep'] = done('42\n')
            self.assertEqual(sm.sync_app(setup, app, self.root, 'arm64'), ('Hotkeys 0.1.0 -> 1234567 available; quit Hotkeys and rerun sync', 'warn'))
            self.assertEqual(len(runs), 1)
        self.assertEqual((self.root / sm.STATE_DIR / 'Hotkeys.commit').read_text(), 'abcdef0123\n')
        plan = self.setup('--plan', '--profile', 'mac')
        with patch.object(plan, 'read', side_effect=lambda a: reads['git'] if a[0] == 'git' else done('', 1)), patch.object(m.subprocess, 'run', side_effect=AssertionError('ran')):
            self.assertEqual(sm.sync_app(plan, app, self.root, 'arm64'), ('Hotkeys 0.1.0 -> 1234567 (would build)', 'ok'))

    def test_running_app_is_not_replaced(self):
        setup = self.setup('--profile', 'mac')
        make_app(self.root / 'Tasks.app', 'com.x.tasks', '0.2.0')
        reads = {'gh': done('v0.2.1\n'), 'pgrep': done('123\n')}
        with patch.object(setup, 'read', side_effect=lambda a: reads[a[0]]), patch.object(sm, 'install_release', side_effect=AssertionError('replaced')):
            detail, state = sm.sync_app(setup, APP, self.root, 'arm64')
        self.assertIn('quit Tasks', detail)
        self.assertEqual(state, 'warn')

    def fake_run(self, version):
        def run(argv, **kwargs):
            if argv[0] == 'ditto':
                make_app(Path(argv[-1]) / 'Tasks.app', 'com.x.tasks', version)
        return run

    def test_install_release_replaces_bundle_and_strips_quarantine(self):
        setup = self.setup('--profile', 'mac')
        target = self.root / 'Tasks.app'
        make_app(target, 'com.x.tasks', '0.2.0')
        with patch.object(setup, 'run', side_effect=self.fake_run('0.2.1')) as run:
            sm.install_release(setup, DOWNLOAD, 'v0.2.1', target)
        self.assertEqual(sm.installed_version(target, 'com.x.tasks'), '0.2.1')
        self.assertEqual([p.name for p in self.root.iterdir()], ['Tasks.app'])
        self.assertEqual(run.call_args.args[0][:3], ['xattr', '-dr', 'com.apple.quarantine'])

    def test_failed_move_restores_old_bundle(self):
        setup = self.setup('--profile', 'mac')
        target = self.root / 'Tasks.app'
        make_app(target, 'com.x.tasks', '0.2.0')
        real = sm.shutil.move
        calls = []
        def move(src, dst):
            calls.append(src)
            if len(calls) == 2:
                raise OSError('disk full')
            return real(src, dst)
        with patch.object(setup, 'run', side_effect=self.fake_run('0.2.1')), patch.object(sm.shutil, 'move', side_effect=move):
            with self.assertRaises(OSError):
                sm.install_release(setup, DOWNLOAD, 'v0.2.1', target)
        self.assertEqual(sm.installed_version(target, 'com.x.tasks'), '0.2.0')

    def test_old_bundle_staged_beside_target_and_restored_on_interrupt_or_partial_copy(self):
        target = self.root / 'Tasks.app'
        make_app(target, 'com.x.tasks', '0.2.0')
        new = self.root / 'new' / 'Tasks.app'
        make_app(new, 'com.x.tasks', '0.2.1')
        real = sm.shutil.move
        seen = []
        def move(src, dst):
            seen.append(Path(dst))
            if len(seen) == 2:
                Path(dst).mkdir()  # half-copied bundle
                raise KeyboardInterrupt
            return real(src, dst)
        with patch.object(sm.shutil, 'move', side_effect=move):
            with self.assertRaises(KeyboardInterrupt):
                sm.replace_bundle(new, target)
        self.assertEqual(seen[0].parent, target.parent)
        self.assertTrue(seen[0].name.startswith('.Tasks.app.old-'))
        self.assertEqual(sm.installed_version(target, 'com.x.tasks'), '0.2.0')
        self.assertTrue(new.exists())

    def test_replace_bundle_removes_leftover_stashes_only_beside_a_live_app(self):
        target = self.root / 'Tasks.app'
        leftover = self.root / '.Tasks.app.old-deadbeef'
        leftover.mkdir()
        new = self.root / 'new' / 'Tasks.app'
        make_app(new, 'com.x.tasks', '0.2.1')
        sm.replace_bundle(new, target)  # no live app: leftovers are kept
        self.assertTrue(leftover.exists())
        make_app(new, 'com.x.tasks', '0.2.2')
        sm.replace_bundle(new, target)
        self.assertFalse(leftover.exists())
        self.assertEqual([p.name for p in self.root.iterdir() if p.name != 'new'], ['Tasks.app'])

    def test_first_move_failure_never_removes_the_original(self):
        target = self.root / 'Tasks.app'
        make_app(target, 'com.x.tasks', '0.2.0')
        with patch.object(sm.shutil, 'move', side_effect=OSError('busy')):
            with self.assertRaises(OSError):
                sm.replace_bundle(self.root / 'x', target)
        self.assertEqual(sm.installed_version(target, 'com.x.tasks'), '0.2.0')

    def test_downloaded_bundle_older_than_tag_is_rejected(self):
        setup = self.setup('--profile', 'mac')
        target = self.root / 'Tasks.app'
        make_app(target, 'com.x.tasks', '0.2.0')
        with patch.object(setup, 'run', side_effect=self.fake_run('0.2.0')):
            with self.assertRaisesRegex(RuntimeError, 'older than release'):
                sm.install_release(setup, DOWNLOAD, 'v0.2.1', target)
        self.assertEqual(sm.installed_version(target, 'com.x.tasks'), '0.2.0')

    def test_install_commands_carry_timeouts(self):
        setup = self.setup('--profile', 'mac')
        target = self.root / 'Tasks.app'
        with patch.object(setup, 'run', side_effect=self.fake_run('0.2.1')) as run:
            sm.install_release(setup, DOWNLOAD, 'v0.2.1', target)
        self.assertTrue(all(c.kwargs['timeout'] == sm.NET_TIMEOUT for c in run.call_args_list))

    def test_apps_plan_makes_no_changes(self):
        setup = self.setup('--plan', '--profile', 'mac')
        make_app(self.root / 'Tasks.app', 'com.jyesselman.tasks', '0.2.0')
        make_app(self.root / 'notes.app', 'com.jyesselman.notes', '0.2.0')
        reads = {'gh': done('v0.2.1\n'), 'pgrep': done('', 1)}
        with patch.object(setup, 'read', side_effect=lambda a: reads[a[0]]), patch.object(m.subprocess, 'run', side_effect=AssertionError('ran')), \
                patch.object(sm.shutil, 'move', side_effect=AssertionError('moved')), patch.object(sm.platform, 'machine', return_value='arm64'):
            result = sm.apps(setup, 'laptop', self.root)
        self.assertIn('Tasks 0.2.0 -> 0.2.1 (would install)', result.details)
        self.assertEqual(sm.installed_version(self.root / 'Tasks.app', 'com.jyesselman.tasks'), '0.2.0')
        self.assertEqual(result.status, 'warn')

    def test_apps_skipped_off_mac_or_unknown_class_and_failure_isolated(self):
        self.assertEqual(sm.apps(self.setup('--profile', 'linux'), 'linux', self.root).status, 'skipped')
        setup = self.setup('--profile', 'mac')
        self.assertEqual(sm.apps(setup, 'mac', self.root).status, 'skipped')
        with patch.object(setup, 'read', return_value=done('', 1, 'no auth')), patch.object(sm.platform, 'machine', return_value='arm64'):
            result = sm.apps(setup, 'laptop', self.root)
        self.assertEqual(result.status, 'failed')
        self.assertEqual(len(result.details), 5)  # apps, Search bundle, and GUI/F4 convergence

    def search_icon(self, setup, data=b'icns'):
        icon = setup.checkout('s') / 'src/search_cli/assets/search-lens.icns'
        icon.parent.mkdir(parents=True, exist_ok=True)
        icon.write_bytes(data)

    def test_search_app_writes_launcher_bundle_once_and_tracks_the_icon(self):
        setup = self.setup('--profile', 'mac')
        self.assertEqual(sm.search_app(setup, self.root)[1], 'warn')  # no checkout yet
        self.search_icon(setup)
        self.assertEqual(sm.search_app(setup, self.root), ('Search CLI launcher installed', 'changed'))
        bundle = self.root / sm.SEARCH_APP
        self.assertEqual(plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())['CFBundleIdentifier'], sm.SEARCH_APP_ID)
        launcher = bundle / 'Contents/MacOS/search-cli'
        self.assertIn('"$HOME/.local/bin/s" gui', launcher.read_text())
        self.assertTrue(launcher.stat().st_mode & 0o100)
        self.assertEqual(sm.search_app(setup, self.root)[1], 'ok')
        self.search_icon(setup, b'new')
        self.assertEqual(sm.search_app(setup, self.root), ('Search CLI launcher updated', 'changed'))
        self.assertEqual((bundle / 'Contents/Resources/search-lens.icns').read_bytes(), b'new')

    def test_search_app_plan_writes_nothing(self):
        setup = self.setup('--plan', '--profile', 'mac')
        self.search_icon(setup)
        detail, state = sm.search_app(setup, self.root)
        self.assertEqual(state, 'ok')
        self.assertIn('would write', detail)
        self.assertFalse((self.root / sm.SEARCH_APP).exists())

    def test_load_apps_validates(self):
        self.assertEqual(len(sm.load_apps(Path(__file__).with_name('apps.json'))), 3)
        bad = self.root / 'a.json'
        bad.write_text('{"format": 1, "apps": [{"name": "x"}]}')
        with self.assertRaises(ValueError):
            sm.load_apps(bad)


if __name__ == '__main__':
    unittest.main()


class KarabinerHealthTests(Base):
    LOAD = '[2026-10-17 13:51:18.399] [info] [console_user_server] Load /h/.config/karabiner/karabiner.json...\n'
    GRAB = '[2026-10-17 12:23:43.239] [info] [core_service (daemon)] K1-Keyboard (device_id:4363372044) hid device events monitor is started (grabbed).\n' \
           '[2026-10-17 12:23:43.267] [info] [core_service (daemon)] G403 HERO Gaming Mouse (device_id:4294973522) hid device events monitor is started (grabbed).\n'

    def paths(self, app=True):
        paths = {k: str(self.root / v.lstrip('/')) if k in ('app', 'daemon') else v for k, v in sm.KARABINER.items()}
        config = self.root / paths['config']
        config.parent.mkdir(parents=True)
        config.write_text('{}')
        os.utime(config, (0, 0))  # edited long before any log line
        if app:
            Path(paths['app']).mkdir(parents=True)
        (self.root / paths['loads']).parent.mkdir(parents=True)
        return paths

    def test_healthy_config_lists_grabbed_keyboards_only(self):
        paths = self.paths()
        (self.root / paths['loads']).write_text(self.LOAD)
        Path(paths['daemon']).parent.mkdir(parents=True)
        Path(paths['daemon']).write_text(self.GRAB)
        setup = self.setup('sync')
        setup.read = lambda argv, **kw: done()
        self.assertEqual(sm.karabiner_health(setup, paths), ([], ['Karabiner grabs: K1-Keyboard']))

    def test_stale_load_errors_and_no_keyboard_are_problems(self):
        paths = self.paths()
        (self.root / paths['loads']).write_text(
            '[2020-01-01 00:00:00.000] [info] [console_user_server] Load /h/.config/karabiner/karabiner.json...\n'
            '[2020-01-01 00:00:01.000] [error] [console_user_server] shell_command stderr:/bin/sh: x: No such file\n')
        os.utime(self.root / paths['config'], None)  # edited now, after the 2020 load
        setup = self.setup('sync')
        setup.read = lambda argv, **kw: done(code=1)
        problems, notes = sm.karabiner_health(setup, paths)
        self.assertEqual(notes, [])
        self.assertEqual([p.split(':')[0] for p in problems],
                         ['Karabiner daemon not running', 'karabiner.json was edited after Karabiner last loaded it (2020-01-01 00',
                          'Karabiner error', 'Karabiner grabs no keyboard'])

    def test_missing_app_or_config_short_circuits(self):
        paths = self.paths(app=False)
        setup = self.setup('sync')
        self.assertEqual(sm.karabiner_health(setup, paths)[0], ['Karabiner-Elements not installed, so karabiner.json does nothing (brew bundle installs it)'])
        (self.root / paths['config']).unlink()
        self.assertEqual(sm.karabiner_health(setup, paths), ([], []))
