"""Regression checks run entirely in temporary directories, without installers."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
import unittest.mock
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def setup(self, *argv):
        return m.Setup(m.parse(list(argv)), root=self.root)

    def test_plan_is_read_only_for_both_platforms_and_options(self):
        for profile in ['mac', 'linux', 'cluster']:
            args = ['--plan', '--profile', profile, '--games', '--search', '--previews']
            if profile == 'mac':
                args.append('--desktop')
            empty = subprocess.CompletedProcess([], 0, '', '')
            with patch.object(m.subprocess, 'run', side_effect=AssertionError('plan ran a process')), patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('plan downloaded')), patch.object(m.Setup, 'read', return_value=empty):
                self.assertEqual(self.setup(*args).execute(), 0)
            self.assertEqual(list(self.root.iterdir()), [])
        self.assertIn('No files changed', self.output.getvalue())

    def test_unique_backup_and_repeat_links(self):
        setup = self.setup('--profile', 'mac')
        source = self.root / 'tracked.json'; source.write_text('new')
        dest = self.root / 'app/settings.json'; dest.parent.mkdir(); dest.write_text('original')
        old = dest.with_name('settings.json.bak'); old.write_text('older backup')
        setup.link(source, dest); setup.link(source, dest)
        self.assertEqual(dest.read_text(), 'new')
        backups = list(dest.parent.glob('settings.json.backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'original')
        self.assertEqual(old.read_text(), 'older backup')

    def test_dangling_symlink_is_preserved(self):
        setup = self.setup('--profile', 'mac')
        source = self.root / 'tracked'; source.write_text('new')
        dest = self.root / 'settings'; dest.symlink_to(self.root / 'missing')
        setup.link(source, dest)
        self.assertTrue(next(self.root.glob('settings.backup-*')).is_symlink())

    def test_existing_dirty_checkout_is_not_updated(self):
        setup = self.setup('--profile', 'mac')
        dest = self.root / 'plugin'; (dest / '.git').mkdir(parents=True)
        (dest / 'init').write_text('my local edits')
        with patch.object(setup, 'run', side_effect=AssertionError('modified checkout')):
            setup.clone('https://example.invalid/plugin', dest, 'abc', 'init')
        self.assertEqual((dest / 'init').read_text(), 'my local edits')

    def test_incomplete_checkout_fails_instead_of_false_success(self):
        setup = self.setup('--profile', 'mac')
        dest = self.root / 'partial'; dest.mkdir()
        with self.assertRaises(RuntimeError):
            setup.clone('https://example.invalid/plugin', dest, sentinel='init')

    def test_linux_repeat_creates_only_command_wrappers(self):
        setup = self.setup('--profile', 'linux')
        specs = [s.strip() for s in (m.HERE / 'linux-packages.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
        (setup.envdir / 'bin').mkdir(parents=True)
        for name in m.TOOLS:
            tool = setup.envdir / 'bin' / name
            tool.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n'); tool.chmod(0o755)
        (setup.envdir / '.dotfiles-manifest').write_text(m.hashlib.sha256('\n'.join(specs).encode()).hexdigest())
        with patch.object(setup, 'run', side_effect=AssertionError('rerun installed packages')), patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('rerun downloaded')):
            setup.linux_tools(); setup.linux_tools()
        self.assertFalse((setup.shims / 'python3').exists())
        output = subprocess.check_output([str(setup.shims / 'fzf'), 'path with spaces', 'semi;colon'], text=True)
        self.assertEqual(output, 'path with spaces\nsemi;colon\n')

    def test_failures_return_nonzero_and_are_reported(self):
        setup = self.setup('--profile', 'mac', '--skip-packages', '--skip-nvim')
        with patch.object(setup, 'shell', side_effect=RuntimeError('network unavailable')), patch.object(setup, 'tmux'), patch.object(setup, 'tool'), patch.object(setup, 'doctor', return_value=['missing yazi']):
            self.assertEqual(setup.execute(), 1)
        self.assertIn('Setup incomplete', self.output.getvalue())
        self.assertIn('network unavailable', self.output.getvalue())

    def test_versions(self):
        self.assertLess(m.version('tmux 2.7'), m.MINIMUM['tmux'])
        self.assertGreaterEqual(m.version('tmux 3.6a'), m.MINIMUM['tmux'])
        self.assertGreaterEqual(m.version('NVIM v0.11.5'), m.MINIMUM['nvim'])
        self.assertGreaterEqual(m.version('Yazi\n Version: 26.9.1'), m.MINIMUM['yazi'])

    def test_desktop_is_opt_in(self):
        setup = self.setup('--plan', '--profile', 'mac')
        setup.packages()
        self.assertNotIn('Brewfile.desktop', self.output.getvalue())
        self.assertNotIn('Brewfile.previews', self.output.getvalue())

    def test_doctor_never_installs(self):
        setup = self.setup('--doctor', '--profile', 'linux')
        with patch.object(setup, 'find', return_value=None), patch.object(setup, 'run', side_effect=AssertionError('doctor ran installer')):
            self.assertEqual(setup.execute(), 1)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_read_runs_in_plan_mode_and_maps_missing_binary_to_127(self):
        setup = self.setup('--plan', '--profile', 'linux')
        self.assertEqual(setup.read(['sh', '-c', 'printf hi']).stdout, 'hi')
        missing = setup.read(['definitely-not-a-binary-xyz'])
        self.assertEqual(missing.returncode, 127)
        self.assertEqual(setup.read(['sleep', '5'], timeout_s=0.1).returncode, 124)

    def test_phase_returns_value_and_records_value_error(self):
        setup = self.setup('--profile', 'linux')
        self.assertEqual(setup.phase('ok', lambda: 7), 7)
        def bad():
            raise ValueError('bad json')
        self.assertIsNone(setup.phase('Parse', bad))
        self.assertEqual(setup.errors, ['Parse: bad json'])

    def test_two_legacy_action_flags_are_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            m.main(['--doctor', '--sync'])

    def test_legacy_flags_become_subcommands(self):
        self.assertEqual(m.normalize(['--sync', '--plan']), ['sync', '--plan'])
        self.assertEqual(m.normalize(['--plan', '--profile', 'linux']), ['setup', '--plan', '--profile', 'linux'])
        self.assertEqual(m.normalize(['--install-schedule']), ['schedule'])
        self.assertEqual(m.normalize(['doctor', '--search']), ['doctor', '--search'])
        self.assertEqual(m.normalize([]), ['setup'])
        self.assertEqual(m.normalize(['-h']), ['-h'])
        args = m.parse(['--doctor', '--search'])
        self.assertEqual((args.command, args.search, args.plan), ('doctor', True, False))

    def test_main_dispatches_commands_to_sync_modules(self):
        import sync, sync_schedule
        with patch.object(sync, 'Sync') as engine, patch.object(sync_schedule, 'install', return_value=4):
            engine.return_value.execute.return_value = 3
            self.assertEqual(m.main(['sync', '--plan', '--profile', 'linux']), 3)
            self.assertEqual(m.main(['--sync', '--plan', '--profile', 'linux']), 3)
            self.assertEqual(m.main(['schedule', '--profile', 'linux']), 4)

    def test_run_env_override(self):
        setup = self.setup('--profile', 'linux')
        with patch.object(m.subprocess, 'run') as run:
            setup.run(['echo', 'x'], env={'A': '1'}, stdin=subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs['env'], {'A': '1'})
        self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)

    def test_doctor_reports_absolute_home_path_as_needs_attention(self):
        setup = self.setup('--doctor', '--profile', 'linux')
        (self.root / 'rc').write_text('a\nb\nexport X=/home/' + 'jyesselm/data\n')
        listing = subprocess.CompletedProcess([], 0, 'rc\0', '')
        with patch.object(setup, 'find', side_effect=lambda n: 'yadm' if n == 'yadm' else None), patch.object(setup, 'read', return_value=listing):
            failures = setup.doctor()
        self.assertIn('Absolute home path: rc:3', failures)

    def test_doctor_checks_login_shell_resolves_grc_and_s_to_uv_installs(self):
        setup = self.setup('--doctor', '--profile', 'linux', '--search')
        (self.root / '.local/bin').mkdir(parents=True)

        def read(argv, **kwargs):
            if argv[0] == 'zsh':
                self.assertEqual(argv[1], '-ilc')
                return subprocess.CompletedProcess(argv, 0, 'grc=%s\ns=/opt/conda/bin/s\n' % (self.root / '.local/bin/grc'), '')
            return subprocess.CompletedProcess(argv, 1, '', '')
        with patch.object(setup, 'find', side_effect=lambda n: 'zsh' if n == 'zsh' else None), patch.object(setup, 'read', side_effect=read):
            failures = setup.doctor()
        self.assertEqual([f for f in failures if 'resolves to' in f],
                         ['s resolves to /opt/conda/bin/s in a login shell, not ~/.local/bin/s (uv install): check PATH order in ~/.zsh/tools.zsh'])
        with patch.object(setup, 'find', return_value=None):
            self.assertEqual(setup.shell_path(), [])

    def test_editors_link_cursor_settings_and_keybindings_only(self):
        setup = self.setup('--profile', 'linux')
        files = self.root / '.config/yadm/files'; files.mkdir(parents=True)
        for target in ['settings.json', 'keybindings.json']:
            (files / ('cursor-' + target)).write_text('cursor')
            (files / ('vscode-' + target)).write_text('stale')
        for app in ['Code', 'Cursor']:
            (self.root / '.config' / app / 'User').mkdir(parents=True)
        setup.editors()
        links = [p for p in (self.root / '.config').glob('*/User/*.json') if p.is_symlink()]
        self.assertEqual(sorted(p.parent.parent.name for p in links), ['Cursor', 'Cursor'])

    def test_protect_live_keeps_differing_files_and_links_missing_or_identical(self):
        setup = self.setup('--profile', 'linux')
        files = self.root / '.config/yadm/files'; files.mkdir(parents=True)
        for target in ['settings.json', 'keybindings.json']:
            (files / ('cursor-' + target)).write_text('tracked')
        user = self.root / '.config/Cursor/User'; user.mkdir(parents=True)
        (user / 'settings.json').write_text('my live edits')
        held = setup.editors(protect_live=True)
        self.assertEqual(held, [str(user / 'settings.json')])
        self.assertEqual((user / 'settings.json').read_text(), 'my live edits')
        self.assertFalse((user / 'settings.json').is_symlink())
        self.assertTrue((user / 'keybindings.json').is_symlink())
        (user / 'settings.json').write_text('tracked')
        self.assertEqual(setup.editors(protect_live=True), [])
        self.assertTrue((user / 'settings.json').is_symlink())

    def test_run_with_timeout_uses_own_session_and_kills_group(self):
        setup = self.setup('--profile', 'linux')
        proc = unittest.mock.MagicMock(pid=4242)
        proc.__enter__.return_value = proc
        proc.wait.side_effect = [subprocess.TimeoutExpired('x', 1), 0]
        with patch.object(m.subprocess, 'Popen', return_value=proc) as popen, patch.object(m.os, 'killpg') as killpg:
            with self.assertRaises(subprocess.TimeoutExpired):
                setup.run(['sleep', '9'], timeout=1)
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        killpg.assert_called_once_with(4242, m.signal.SIGKILL)

    def test_run_with_timeout_reports_failure_exit(self):
        setup = self.setup('--profile', 'linux')
        with self.assertRaises(subprocess.CalledProcessError):
            setup.run(['sh', '-c', 'exit 3'], timeout=5)
        setup.run(['true'], timeout=5)

    def test_tool_installs_editable_from_developing_checkout(self):
        setup = self.setup('--profile', 'mac', '--search')
        for command, (repo, extras) in m.CHECKOUT_TOOLS.items():
            checkout = self.root / m.DEVELOPING / repo
            (checkout / '.git').mkdir(parents=True)
            (checkout / 'pyproject.toml').write_text('[project]\n')
            with patch.object(setup, 'run') as run:
                setup.tool(command)
            run.assert_called_once_with(['uv', 'tool', 'install', '--python', '3.12', '--editable', str(checkout) + extras])
            self.assertNotIn('repos/' + repo, str(run.call_args))
        self.assertEqual(m.CHECKOUT_TOOLS['s'][1], '[gui,docs]')  # `s gui` and document previews on every machine

    def test_tool_plan_clones_missing_checkout_into_developing(self):
        self.setup('--plan', '--profile', 'linux').tool('grc')
        self.assertIn('git-repo-checker.git -> ' + str(self.root / m.DEVELOPING / 'git-repo-checker'), self.output.getvalue())

    def test_bootstrap_installs_grc_without_a_flag(self):
        setup = self.setup('--plan', '--profile', 'linux', '--skip-packages', '--skip-nvim')
        with patch.object(setup, 'phase') as phase:
            setup.execute()
        self.assertIn('Repo checker (grc) from its developing checkout', [c.args[0] for c in phase.call_args_list])

    def test_read_ok_raises_with_stderr(self):
        setup = self.setup('--profile', 'linux')
        self.assertEqual(setup.read_ok(['sh', '-c', 'printf hi'], 'x'), 'hi')
        with self.assertRaisesRegex(RuntimeError, 'boom failed: oops'):
            setup.read_ok(['sh', '-c', 'echo oops >&2; exit 3'], 'boom failed')


if __name__ == '__main__':
    unittest.main()


class MachineClassTests(BootstrapTests):
    def test_class_falls_back_when_unset_but_fails_when_yadm_breaks(self):
        setup = self.setup('sync', '--profile', 'mac')
        setup.find = lambda name: '/bin/yadm' if name == 'yadm' else None
        setup.read = lambda argv, **kw: subprocess.CompletedProcess(argv, 1, '', '')  # unset
        self.assertEqual(setup.machine_class(), 'mac')
        setup = self.setup('sync', '--profile', 'mac')
        setup.find = lambda name: '/bin/yadm' if name == 'yadm' else None
        setup.read = lambda argv, **kw: subprocess.CompletedProcess(argv, 124, '', 'timed out after 60s')
        with self.assertRaisesRegex(RuntimeError, 'local.class failed'):
            setup.machine_class()
        setup = self.setup('sync', '--profile', 'mac')
        setup.find = lambda name: '/bin/yadm' if name == 'yadm' else None
        setup.read = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, 'studio\n', '')
        self.assertEqual(setup.machine_class(), 'studio')
