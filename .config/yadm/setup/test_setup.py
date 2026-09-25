"""Regression checks run entirely in temporary directories, without installers."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
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
        return m.Setup(m.parser().parse_args(list(argv)), root=self.root)

    def test_plan_is_read_only_for_both_platforms_and_options(self):
        for profile in ['mac', 'linux', 'cluster']:
            args = ['--plan', '--profile', profile, '--games', '--search', '--previews']
            if profile == 'mac':
                args.append('--desktop')
            with patch.object(m.subprocess, 'run', side_effect=AssertionError('plan ran a process')), patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('plan downloaded')):
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
        with patch.object(setup, 'shell', side_effect=RuntimeError('network unavailable')), patch.object(setup, 'tmux'), patch.object(setup, 'doctor', return_value=['missing yazi']):
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


if __name__ == '__main__':
    unittest.main()
