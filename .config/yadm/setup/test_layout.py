"""Layout manifest and portability scan, in temporary directories only."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import layout as lay

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

J = '/home/' + 'jyesselm'
U = 'jyesselman' + '2'
TEXT = '''# comment
a/b
c  profile:mac
d  profile:linux class:laptop
e/f  profile:mac check
'''


class LayoutTests(unittest.TestCase):
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
        setup = m.Setup(m.parser().parse_args(list(argv)), root=self.root)
        setup._class = 'laptop'
        return setup

    def test_parse_layout_filters_profile_and_class_and_check_flag(self):
        mac = {e.path: e.create for e in lay.parse_layout(TEXT, 'mac', 'laptop')}
        self.assertEqual(mac, {'a/b': True, 'c': True, 'e/f': False})
        linux = [e.path for e in lay.parse_layout(TEXT, 'linux', 'laptop')]
        self.assertEqual(linux, ['a/b', 'd'])
        self.assertEqual([e.path for e in lay.parse_layout(TEXT, 'linux', 'studio')], ['a/b'])
        self.assertEqual(len(lay.parse_layout(TEXT, None, None)), 4)

    def test_parse_layout_rejects_absolute_tilde_dotdot_and_unknown_tokens(self):
        for bad in ['/abs', '~/x', 'a/../b', 'x bogus', 'x profile:windows']:
            with self.assertRaisesRegex(ValueError, 'line 1'):
                lay.parse_layout(bad, 'mac', 'laptop')

    def test_layout_creates_missing_dirs_and_is_idempotent(self):
        setup = self.setup('--profile', 'linux')
        first = setup.layout()
        self.assertTrue((self.root / 'local/code/python').is_dir())
        self.assertGreater(len(first.created), 10)
        self.assertEqual(setup.layout().created, [])

    def test_layout_plan_mode_lists_but_creates_nothing(self):
        setup = self.setup('--plan', '--profile', 'linux')
        setup.layout()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertIn('Create ~/local/code/python', self.output.getvalue())

    def test_check_entry_is_reported_not_created(self):
        report = self.setup('--profile', 'mac').layout()
        self.assertEqual(report.expected, ['cloud/Dropbox'])
        self.assertFalse((self.root / 'cloud/Dropbox').exists())

    def test_unplanned_skips_hidden_standard_and_planned(self):
        for name in ['.hidden', 'Documents', 'cloud', 'stray', 'Another']:
            (self.root / name).mkdir()
        entries = lay.parse_layout(TEXT + 'cloud/x profile:linux\n', None, None)
        self.assertEqual(lay.unplanned_entries(self.root, entries), ['Another', 'stray'])

    def test_ignore_globs_hide_unplanned_entries_and_are_never_created(self):
        for name in ['Google Drive', 'Dropbox (Old)', 'Claude', 'stray']:
            (self.root / name).mkdir()
        entries = lay.parse_layout(TEXT + 'Google*  ignore\nDropbox*  ignore\nClaude  ignore class:laptop\n', None, None)
        self.assertEqual(lay.unplanned_entries(self.root, entries), ['stray'])
        self.assertEqual([e.path for e in lay.missing_dirs(self.root, entries)], ['a/b', 'c', 'd', 'e/f'])
        for bad in ['x  check ignore', 'cloud/x  ignore']:
            with self.assertRaises(ValueError):
                lay.parse_layout(bad, None, None)
        report = self.setup('--profile', 'mac').layout()
        self.assertEqual(report.unplanned, ['stray'])
        self.assertFalse((self.root / 'gdrive').exists())

    def test_portability_finds_planted_home_path_with_file_and_line(self):
        (self.root / 'f.py').write_text('a = 1\nb = 2\nx = "' + J + '/data"\n')
        self.assertEqual(lay.find_home_paths(self.root, 'f.py\0'), (['f.py:3'], []))

    def test_portability_does_not_match_longer_username(self):
        (self.root / 'f').write_text(J + '2x/a\n/Users/' + U + '/b\n' + J + '/c\n')
        hits, _ = lay.find_home_paths(self.root, 'f\0')
        self.assertEqual(hits, ['f:2', 'f:3'])

    def test_portability_known_exceptions_and_binary_skipped(self):
        known = next(iter(lay.KNOWN_ABSOLUTE))
        (self.root / known).parent.mkdir(parents=True)
        (self.root / known).write_text('/Users/' + U + '/x\n')
        (self.root / 'bin').write_bytes(b'\0/Users/' + U.encode())
        (self.root / 'link').symlink_to(self.root / 'bin')
        hits, found = lay.find_home_paths(self.root, '\0'.join([known, 'bin', 'link', 'gone']) + '\0')
        self.assertEqual((hits, found), ([], [known + ':1']))


if __name__ == '__main__':
    unittest.main()
