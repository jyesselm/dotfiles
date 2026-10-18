"""Linux hotkeys: Toshy slice splicing and GNOME dconf convergence, with fake commands."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sync_linux as sl

CONFIG = ('head\n###  SLICE_MARK_START: user_apps  ###  EDITS OUTSIDE\nold\n###  SLICE_MARK_END: user_apps  ###  EDITS\n'
          '###  SLICE_MARK_START: kbtype_override  ###  X\nkb = {}\n###  SLICE_MARK_END: kbtype_override  ###  X\ntail\n')
USER = '# header\n### toshy-slice: user_apps\nkeymap("new", {})\n\n### toshy-slice: kbtype_override\nkb = {"K1": "Windows"}\n'
DCONF = '# comment\n[org/gnome/mutter]\noverlay-key=\'\'\n[org/gnome/desktop/wm/keybindings]\nswitch-windows=[\'<Super>Tab\']\n'


def done(out='', code=0):
    return subprocess.CompletedProcess([], code, out, '')


class FakeSetup:
    def __init__(self, root, plan, dconf, active='active'):
        self.root, self.args, self.dconf, self.active, self.runs = root, SimpleNamespace(plan=plan), dconf, active, []

    def read(self, argv, **kwargs):
        if argv[:2] == ['dconf', 'read']:
            return done(self.dconf.get(argv[2], '') + '\n')
        if argv[:2] == ['dconf', 'dump']:
            return done('[old]\n')
        if 'is-active' in argv:
            return done(self.active + '\n')
        return done('log line\n')

    def read_ok(self, argv, what, **kwargs):
        return self.read(argv).stdout

    def run(self, argv, **kwargs):
        if not self.args.plan:
            self.runs.append(argv)


class PureTests(unittest.TestCase):
    def test_splice_replaces_only_named_slices_and_is_idempotent(self):
        once = sl.splice(CONFIG, sl.user_slices(USER))
        self.assertIn('keymap("new", {})', once)
        self.assertIn('kb = {"K1": "Windows"}', once)
        self.assertNotIn('\nold\n', once)
        self.assertTrue(once.startswith('head\n') and once.endswith('tail\n'))
        self.assertEqual(sl.splice(once, sl.user_slices(USER)), once)

    def test_missing_slice_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'no user_custom_functions slice'):
            sl.splice(CONFIG, {'user_custom_functions': 'x'})

    def test_dconf_keys_keep_case_and_values(self):
        self.assertEqual(sl.dconf_keys(DCONF), {'/org/gnome/mutter/overlay-key': "''",
                                                '/org/gnome/desktop/wm/keybindings/switch-windows': "['<Super>Tab']"})


class HotkeysTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / sl.HOTKEYS).mkdir(parents=True)
        (self.root / sl.HOTKEYS / 'toshy_user.py').write_text(USER)
        (self.root / sl.HOTKEYS / 'gnome.dconf').write_text(DCONF)
        self.config = self.root / sl.TOSHY
        self.config.parent.mkdir(parents=True)
        self.config.write_text(CONFIG)
        sl.time.sleep = lambda s: None

    def tearDown(self):
        self.temp.cleanup()

    def test_plan_reports_without_writing(self):
        setup = FakeSetup(self.root, True, {})
        status, summary, _ = sl.hotkeys(setup)
        self.assertEqual((status, summary), ('ok', 'would update Toshy slices, 2 GNOME keys'))
        self.assertEqual(self.config.read_text(), CONFIG)
        self.assertEqual(setup.runs, [])

    def test_apply_writes_backs_up_restarts_and_loads(self):
        setup = FakeSetup(self.root, False, {})
        status, summary, _ = sl.hotkeys(setup)
        self.assertEqual((status, summary), ('changed', 'updated Toshy slices, 2 GNOME keys'))
        self.assertEqual(self.config.with_name('toshy_config.before-converge.py').read_text(), CONFIG)
        self.assertEqual(setup.runs, [['systemctl', '--user', 'restart', sl.SERVICE], ['dconf', 'load', '/']])
        self.assertEqual(len(list((self.root / '.local/state/dotfiles').glob('dconf-*.ini'))), 1)

    def test_converged_machine_is_ok(self):
        self.config.write_text(sl.splice(CONFIG, sl.user_slices(USER)))
        setup = FakeSetup(self.root, False, sl.dconf_keys(DCONF))
        self.assertEqual(sl.hotkeys(setup)[:2], ('ok', 'Toshy running, keys match'))
        self.assertEqual(setup.runs, [])

    def test_toshy_down_warns_with_log(self):
        setup = FakeSetup(self.root, False, {}, active='failed')
        status, summary, details = sl.hotkeys(setup)
        self.assertEqual((status, summary), ('warn', 'Toshy is not running'))
        self.assertIn('log line', details)

    def test_missing_toshy_warns(self):
        self.config.unlink()
        self.assertEqual(sl.hotkeys(FakeSetup(self.root, False, {}))[:2], ('warn', 'Toshy not installed, so Mac shortcuts do nothing'))


if __name__ == '__main__':
    unittest.main()
