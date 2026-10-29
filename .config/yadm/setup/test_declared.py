"""Declared vs present (declared.py) with fake observers; no package manager runs and the real home is never read."""
import contextlib
import importlib.util
import io
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import declared as dc
import sync_mac as sm

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bootstrap_setup', HERE / 'setup.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def done(out='', code=0, err=''):
    return subprocess.CompletedProcess([], code, out, err)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        (self.assets / dc.DECLARED_DIR).mkdir(parents=True)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()
        self.calls = {}  # 'flatpak list --app ...' -> stdout (or CompletedProcess)
        self.runs = []
        self.tools = {'apt-mark', 'snap', 'flatpak', 'gnome-extensions', 'osascript'}

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def setup(self, *argv, cls='laptop'):
        setup = m.Setup(m.parse(['sync', *argv]), root=self.root, assets=self.assets)
        setup._class = cls
        setup.find = lambda name: '/bin/' + name if name in self.tools else None
        setup.read = self.read
        setup.run = self.run_cmd
        return setup

    def read(self, argv, cwd=None, timeout_s=60, input=None):
        value = self.calls.get(' '.join(map(str, argv)), done('', 1, 'not stubbed'))
        return value if isinstance(value, subprocess.CompletedProcess) else done(value)

    def run_cmd(self, argv, **kwargs):
        self.runs.append(' '.join(map(str, argv)))

    def declare(self, kind, text):
        (self.assets / dc.DECLARED_DIR / (kind + '.txt')).write_text(text)

    def apps(self, *names, where='Applications'):
        for name in names:
            (self.root / where / (name + '.app')).mkdir(parents=True)

    def app_dirs(self):
        """Point the apps observer at temp directories instead of /Applications and /System/Applications."""
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(dc, 'APP_DIRS', (str(self.root / 'Applications'), '~/Home Apps')))
        stack.enter_context(patch.object(dc, 'SYSTEM_APPS', str(self.root / 'System')))
        return stack


class ParseTests(Base):
    def test_every_qualifier_names_with_spaces_and_comments(self):
        entries = dc.parse('# header\n\nMicrosoft Word  source:brew  cask:microsoft-office  class:laptop,studio\n'
                           'Thing  source:manual  url:https://example.org/x.dmg  allowed  # a comment\n'
                           'zoom.us source:brew\n')
        word, thing, zoom = entries
        self.assertEqual((word.name, word.source, word.qualifiers['cask'], word.classes, word.allowed),
                         ('Microsoft Word', 'brew', 'microsoft-office', {'laptop', 'studio'}, False))
        self.assertEqual((thing.name, thing.allowed, thing.qualifiers['url']), ('Thing', True, 'https://example.org/x.dmg'))
        self.assertIsNone(zoom.classes)
        self.assertEqual(dc.parse('a.b.c\n', ('class',))[0].source, '')

    def test_bad_qualifiers_name_the_line(self):
        for bad in ['X  source:pip', 'X  source:brew  class:desk', 'X  source:manual  url:http://plain', 'X  colour:red',
                    'X  cask:']:
            with self.assertRaisesRegex(ValueError, 'line 1: bad qualifier'):
                dc.parse(bad)
        with self.assertRaisesRegex(ValueError, 'line 2: Y needs source:'):
            dc.parse('X  source:brew\nY  class:laptop\n')
        with self.assertRaisesRegex(ValueError, 'bad qualifier'):
            dc.parse('pkg  source:brew\n', ('class',))  # only apps take source:

    def test_compare_class_filter_allowed_and_a_wanted_plus_allowed_pair(self):
        entries = dc.parse('A  class:laptop\nB  class:studio\nC\nD  allowed\nB  allowed\n', ('class',))
        self.assertEqual(dc.compare(entries, ['C', 'D', 'E', 'B'], 'laptop'), (['A'], ['E']))
        self.assertEqual(dc.compare(entries, ['A'], 'studio'), (['B', 'C'], ['A']))  # wanted elsewhere is undeclared here
        self.assertEqual(dc.compare([], [], 'laptop'), ([], []))


class ObserverTests(Base):
    def test_apps_observe_three_dirs_and_ignore_apple_and_system_apps(self):
        self.apps('Slack', 'Safari', 'Stray', '.Hidden')
        self.apps('Own', where='Home Apps')
        self.apps('Calculator', where='System')
        self.declare('apps', 'Slack  source:brew\nCalculator  source:system\nOwn  source:manual  allowed\nMissing  source:mas  class:laptop\n')
        with self.app_dirs():
            self.assertEqual(dc.observe_apps(self.setup()), ['Calculator', 'Own', 'Safari', 'Slack', 'Stray'])
            outcome = dc.check(self.setup(), dc.KINDS['apps'], 'laptop')
        self.assertEqual(([e.name for e in outcome.missing], outcome.undeclared), (['Missing'], ['Stray']))
        self.assertEqual(outcome.details(), ['missing:Missing (apps)', 'undeclared:Stray (apps)', 'Missing: App Store: search "Missing"'])

    def test_agents_use_plist_labels_and_skip_vendor_agents(self):
        agents = self.root / 'Library/LaunchAgents'
        agents.mkdir(parents=True)
        (agents / 'file-name.plist').write_bytes(plistlib.dumps({'Label': 'com.yesselman.real'}))
        (agents / 'com.broken.plist').write_text('not a plist')
        (agents / 'homebrew.mxcl.ollama.plist').write_bytes(plistlib.dumps({'Label': 'homebrew.mxcl.ollama'}))
        self.assertEqual(dc.observe_agents(self.setup()), ['com.broken', 'com.yesselman.real', 'homebrew.mxcl.ollama'])
        outcome = dc.check(self.setup(), dc.KINDS['agents'], 'laptop')
        self.assertEqual(outcome.undeclared, ['com.broken', 'com.yesselman.real'])

    def test_login_items_failure_is_recorded_not_raised(self):
        self.calls['osascript -e tell application "System Events" to get the name of every login item'] = done('', 1, 'denied')
        outcome = dc.check(self.setup(), dc.KINDS['login-items'], 'laptop')
        self.assertIn('System Events did not answer', outcome.error)
        self.assertEqual(outcome.details(), ['login-items: could not list: System Events did not answer (unavailable)'])

    def test_linux_listings_and_absent_tools(self):
        self.calls.update({'snap list': 'Name  Version  Rev\ncore22  2024  1\nfirefox  131.0  2\n',
                           'flatpak list --app --columns=application,version': 'org.zotero.Zotero\t7.0\ncom.x.Y\t\n',
                           'apt-mark showmanual': 'git\nzsh\n', 'gnome-extensions list --enabled': 'a@b\n'})
        setup = self.setup('--profile', 'linux')
        self.assertEqual(dc.snap_versions(setup), {'core22': '2024', 'firefox': '131.0'})
        self.assertEqual(dc.flatpak_versions(setup), {'org.zotero.Zotero': '7.0', 'com.x.Y': ''})
        self.assertEqual((dc.apt_manual(setup), dc.gnome_enabled(setup)), (['git', 'zsh'], ['a@b']))
        self.tools = set()
        self.assertEqual(dc.snap_versions(setup), {})  # no snap here: nothing present, nothing fails


class PhaseTests(Base):
    def linux(self, *argv):
        self.declare('apt', 'git\nvim\nzsh\n')
        self.declare('snap', 'firefox\n')
        self.declare('flatpak', 'org.zotero.Zotero\ncom.slack.Slack\n')
        self.declare('gnome-extensions', 'on@x\noff@x\nabsent@x\n')
        self.calls.update({'apt-mark showmanual': 'git\nzsh\nextra\n', 'snap list': 'Name Version\nfirefox 1\n',
                           'flatpak list --app --columns=application,version': 'org.zotero.Zotero\t7\n',
                           'gnome-extensions list --enabled': 'on@x\n', 'gnome-extensions list': 'on@x\noff@x\n'})
        return self.setup('--profile', 'linux', *argv, cls='linux')

    def test_installers_run_only_for_missing_installable_entries_then_recheck(self):
        def run(argv, **kwargs):
            self.runs.append(' '.join(argv))
            if argv[:2] == ['flatpak', 'install']:
                self.calls['flatpak list --app --columns=application,version'] += argv[-1] + '\t1\n'
        setup = self.linux()
        setup.run = run
        result = dc.declared(setup, 'linux', 'linux')
        self.assertEqual(self.runs, ['flatpak install --user -y flathub com.slack.Slack', 'gnome-extensions enable off@x'])
        self.assertEqual(result.status, 'warn')  # vim (apt), absent@x and off@x (the fake enable changes nothing) remain
        self.assertIn('missing:vim (apt)', result.details)
        self.assertIn('undeclared:extra (apt)', result.details)
        self.assertIn('packages: sudo apt install vim', result.details)
        self.assertIn('absent@x: https://extensions.gnome.org (search "absent@x", Install)', result.details)
        self.assertNotIn('missing:com.slack.Slack (flatpak)', result.details)

    def test_plan_reports_without_installing(self):
        result = dc.declared(self.linux('--plan'), 'linux', 'linux')
        self.assertEqual(self.runs, [])
        self.assertIn('missing:com.slack.Slack (flatpak)', result.details)
        self.assertIn('; 3 would be installed', result.summary)

    def test_ok_changed_and_skipped(self):
        setup = self.linux()
        self.declare('apt', 'git\nzsh\nextra\n')
        self.declare('gnome-extensions', 'on@x\n')
        self.declare('flatpak', 'org.zotero.Zotero\n')
        self.assertEqual(dc.declared(setup, 'linux', 'linux').status, 'ok')
        self.declare('flatpak', 'org.zotero.Zotero\nnew.App\n')
        setup.run = lambda argv, **kw: self.calls.update({'flatpak list --app --columns=application,version': 'org.zotero.Zotero\t7\nnew.App\t1\n'})
        result = dc.declared(setup, 'linux', 'linux')
        self.assertEqual((result.status, result.summary), ('changed', '1 installed; all declared: apt, snap, flatpak, gnome-extensions'))
        self.assertEqual(dc.declared(setup, 'cluster', 'cluster').status, 'skipped')

    def test_broken_declaration_file_fails_the_phase_with_its_name(self):
        setup = self.linux()
        self.declare('snap', 'x  colour:red\n')
        with self.assertRaisesRegex(ValueError, 'declared/snap.txt line 1'):
            dc.declared(setup, 'linux', 'linux')


class GeneratedTests(Base):
    def test_manual_apps_apt_and_undeclared_become_recipes(self):
        self.declare('apps', 'Magnet  source:mas\nTool  source:manual  url:https://example.org/t.dmg\nZed  source:brew\n')
        self.declare('apt', 'vim\ngit\n')
        state = {'declared.apps.missing': ['Magnet', 'Tool', 'Zed'], 'declared.apps.undeclared': ['Stray'],
                 'declared.agents.missing': ['com.x'], 'declared.login-items.missing': 'error: denied'}
        found = dc.pending(self.setup('--profile', 'mac'), state)
        self.assertEqual([(p.name, p.title, p.steps[0]) for p in found], [
            ('install-apps-magnet', 'Install Magnet (apps)', 'App Store: search "Magnet"'),
            ('install-apps-tool', 'Install Tool (apps)', 'download: https://example.org/t.dmg'),
            ('adopt-apps', 'Declare or adopt apps', 'converge status --all (lists the undeclared apps)')])  # brew: packages installs it
        linux = dc.pending(self.setup('--profile', 'linux', cls='linux'), {'declared.apt.missing': ['vim', 'git']})
        self.assertEqual([(p.name, p.steps) for p in linux], [('install-apt-packages', ['sudo apt install vim git', 'converge sync'])])

    def test_snapshot_keys_per_kind(self):
        self.declare('apt', 'git\n')
        self.calls.update({'apt-mark showmanual': 'zsh\n', 'snap list': 'Name Version\n'})
        self.calls['gnome-extensions list --enabled'] = done('', 2, 'no bus')
        values = dc.snapshot(self.setup('--profile', 'linux', cls='linux'))
        self.assertEqual((values['apt.missing'], values['apt.undeclared']), (['git'], ['zsh']))
        self.assertEqual(values['snap.missing'], [])
        self.assertTrue(values['gnome-extensions.missing'].startswith('error: could not list: gnome-extensions failed'))


class AdoptTests(Base):
    def test_adopt_appends_undeclared_under_a_dated_comment_until_clean(self):
        self.declare('apps', 'Slack  source:brew\n')
        self.apps('Slack', 'My Tool')
        with self.app_dirs():
            setup = self.setup('--profile', 'mac')
            setup.args.plan = True
            self.assertEqual(dc.adopt(setup, 'apps'), 0)
            self.assertEqual((self.assets / 'declared/apps.txt').read_text(), 'Slack  source:brew\n')
            setup.args.plan = False
            self.assertEqual(dc.adopt(setup, 'apps'), 0)
            lines = (self.assets / 'declared/apps.txt').read_text().splitlines()
            self.assertTrue(lines[1].startswith('# laptop, adopted 20'))
            self.assertEqual(lines[2], 'My Tool  source:manual  allowed')
            self.assertEqual(dc.check(setup, dc.KINDS['apps'], 'laptop').undeclared, [])
            self.assertEqual(dc.adopt(setup, 'apps'), 0)
        self.assertIn('Nothing to adopt', self.output.getvalue())

    def test_adopt_extras_delegates_and_bad_kinds_raise(self):
        setup = self.setup('--profile', 'mac')
        with patch.object(sm, 'adopt_extras', return_value=0) as extras:
            self.assertEqual(dc.adopt(setup, 'extras'), 0)
        extras.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, 'unknown kind brew'):
            dc.adopt(setup, 'brew')
        with self.assertRaisesRegex(RuntimeError, 'apt are declared on linux machines only'):
            dc.adopt(setup, 'apt')


class ManifestTests(unittest.TestCase):
    """The real setup/declared/ files: they parse, brew apps are Brewfile casks, release apps are in apps.json."""

    def entries(self, kind):
        return dc.parse((HERE / dc.DECLARED_DIR / dc.KINDS[kind].file).read_text(), dc.KINDS[kind].keys)

    def test_every_declaration_file_parses_and_belongs_to_a_kind(self):
        files = sorted(p.name for p in (HERE / dc.DECLARED_DIR).glob('*.txt'))
        self.assertEqual(files, sorted(kind.file for kind in dc.KINDS.values()))
        for kind in dc.KINDS:
            self.assertTrue(self.entries(kind), kind)

    def test_brew_apps_are_casks_and_release_apps_are_in_apps_json(self):
        brewfiles = [HERE / name for name in sorted({n for names in sm.BREWFILES.values() for n in names})]
        casks = set(sm.parse_brewfile(sm.merge_brewfiles(brewfiles)).casks)
        casks |= {e.split(':', 1)[1] for e in sm.parse_extras((HERE / sm.EXTRAS_FILE).read_text()) if e.startswith('cask:')}
        apps = sm.load_apps(HERE / 'apps.json')
        released = {a['name'] for a in apps} | {Path(a['bundle']).stem for a in apps} | {Path(sm.SEARCH_APP).stem}
        for entry in self.entries('apps'):
            if entry.source == 'brew':
                self.assertIn(dc.cask_token(entry), casks, '%s: no such cask in a Brewfile or extras.txt' % entry.name)
            if entry.source == 'release':
                self.assertIn(entry.name, released, '%s: not in apps.json' % entry.name)


if __name__ == '__main__':
    unittest.main()
