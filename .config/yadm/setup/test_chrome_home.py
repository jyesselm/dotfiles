"""Chrome Home setup tests: no installers or browser profiles are touched."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import setup


class ChromeHomeTests(unittest.TestCase):
    def test_plan_mac_and_linux_do_not_write(self):
        for profile in ('mac', 'linux'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as d:
                instance = setup.Setup(setup.parse(['chrome-home', '--plan', '--profile', profile]), root=d)
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    instance.chrome_home()
                self.assertIn('chrome_newtab', out.getvalue())
                self.assertEqual(list(Path(d).iterdir()), [])

    def test_bridge_uses_this_computers_id_and_preserves_settings(self):
        with tempfile.TemporaryDirectory() as d:
            instance = setup.Setup(setup.parse(['chrome-home', '--profile', 'linux', '--extension-id', 'a'*32]), root=d)
            manifest = instance.checkout('s') / 'src/search_cli/chrome_newtab/manifest.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{}')
            config = Path(d) / '.config/search-cli/dashboard.json'
            config.parent.mkdir(parents=True)
            config.write_text('{"pins":[]}')
            with patch.object(instance, 'tool') as install, patch.object(instance, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
                instance.chrome_home()
            install.assert_called_once_with('s')
            run.assert_called_once_with([Path(d)/'.local/bin/s', 'web', '--install-chrome', 'a'*32])
            self.assertEqual(config.read_text(), '{"pins":[]}')
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)

    def test_invalid_id_and_cluster_fail_before_install(self):
        for args in (['--profile','cluster'], ['--profile','mac','--extension-id','invalid']):
            instance = setup.Setup(setup.parse(['chrome-home',*args]))
            with patch.object(instance,'tool') as install:
                with self.assertRaises(RuntimeError):
                    instance.chrome_home()
                install.assert_not_called()
