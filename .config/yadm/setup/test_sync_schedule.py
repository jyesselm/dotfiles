"""Schedule rendering and install behaviour; launchctl and crontab are never run."""
import contextlib
import importlib.util
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_schedule as ss

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ScheduleTests(unittest.TestCase):
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

    def test_launchd_plist_content(self):
        plist = ss.launchd_plist(Path('/h'), '/usr/bin/python3')
        self.assertEqual(plist['Label'], 'com.yesselman.dotfiles-sync')
        self.assertEqual(plist['ProgramArguments'], ['/usr/bin/python3', '/h/.config/yadm/setup/setup.py', '--sync'])
        self.assertEqual(plist['StartCalendarInterval'], {'Hour': 10, 'Minute': 0})
        self.assertTrue(plist['RunAtLoad'])
        self.assertEqual(plist['StandardOutPath'], '/h/.local/state/dotfiles/sync/sync.log')
        self.assertTrue(plist['EnvironmentVariables']['PATH'].startswith('/h/.local/bin:'))

    def test_cron_lines_linux_has_reboot_cluster_does_not(self):
        linux = ss.cron_lines(Path('/h x'), '/usr/bin/python3', 'linux')
        cluster = ss.cron_lines(Path('/h x'), '/usr/bin/python3', 'cluster')
        self.assertEqual((len(linux), len(cluster)), (2, 1))
        self.assertTrue(linux[0].startswith('0 10 * * * PATH='))
        self.assertTrue(linux[1].startswith('@reboot '))
        self.assertTrue(all('GH_PROMPT_DISABLED=1' in line for line in linux + cluster))
        self.assertTrue(all(ss.MARKER in line and "'/h x/" in line for line in linux + cluster))

    def test_merge_crontab_replaces_only_marked_lines(self):
        old = '5 4 * * * backup\n0 9 * * * old # dotfiles-sync\n'
        merged = ss.merge_crontab(old, ['0 10 * * * new # dotfiles-sync'])
        self.assertEqual(merged, '5 4 * * * backup\n0 10 * * * new # dotfiles-sync\n')
        self.assertEqual(ss.merge_crontab('', ['x # dotfiles-sync']), 'x # dotfiles-sync\n')

    def test_cron_unavailable_skips_with_note(self):
        setup = self.setup('--profile', 'cluster')
        for result in [subprocess.CompletedProcess([], 127, '', 'not found'),
                       subprocess.CompletedProcess([], 1, '', 'crontab: you are not allowed to use this program')]:
            with patch.object(setup, 'read', return_value=result), patch.object(setup, 'run', side_effect=AssertionError('ran')):
                self.assertEqual(ss.install(setup), 0)
        self.assertIn('crontab unavailable here; schedule skipped', self.output.getvalue())

    def test_cron_install_handles_empty_crontab_and_pipes_merged_text(self):
        setup = self.setup('--profile', 'linux')
        empty = subprocess.CompletedProcess([], 1, '', 'no crontab for user')
        with patch.object(setup, 'read', return_value=empty), patch.object(setup, 'run') as run:
            self.assertEqual(ss.install(setup), 0)
        self.assertIn('# dotfiles-sync', run.call_args.kwargs['input'])
        self.assertTrue((self.root / ss.STATE_DIR).is_dir())

    def test_install_schedule_plan_writes_nothing(self):
        for profile in ['mac', 'linux']:
            setup = self.setup('--plan', '--profile', profile)
            ok = subprocess.CompletedProcess([], 0, '', '')
            with patch.object(setup, 'read', return_value=ok), patch.object(m.subprocess, 'run', side_effect=AssertionError('ran')):
                self.assertEqual(ss.install(setup), 0)
            self.assertEqual(list(self.root.iterdir()), [])
        self.assertIn('com.yesselman.dotfiles-sync', self.output.getvalue())

    def test_mac_install_writes_plist_and_bootstraps(self):
        setup = self.setup('--profile', 'mac')
        with patch.object(setup, 'read') as read, patch.object(setup, 'run') as run:
            ss.install(setup)
        plist = self.root / 'Library/LaunchAgents/com.yesselman.dotfiles-sync.plist'
        self.assertTrue(plist.exists())
        self.assertEqual(run.call_args.args[0][:2], ['launchctl', 'bootstrap'])
        self.assertEqual(read.call_args.args[0][:2], ['launchctl', 'bootout'])
        self.assertTrue(ss.is_installed(setup))

    def test_is_installed_for_cron(self):
        setup = self.setup('--profile', 'linux')
        with patch.object(setup, 'read', return_value=subprocess.CompletedProcess([], 0, '0 10 * * * x # dotfiles-sync\n', '')):
            self.assertTrue(ss.is_installed(setup))
        with patch.object(setup, 'read', return_value=subprocess.CompletedProcess([], 1, '', '')):
            self.assertFalse(ss.is_installed(setup))


if __name__ == '__main__':
    unittest.main()
