"""Sync orchestration with a fake yadm; nothing touches the real repo, network or home."""
import contextlib
import importlib.util
import io
import json
import plistlib
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sync as sy

spec = importlib.util.spec_from_file_location('bootstrap_setup', Path(__file__).with_name('setup.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

STATUS = 'status --porcelain=v1 -z --untracked-files=no'
PULL = ['yadm', 'pull', '--rebase', '--no-autostash', 'origin', 'main']


def done(out='', code=0, err=''):
    return subprocess.CompletedProcess([], code, out, err)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = io.StringIO()
        self.quiet = contextlib.redirect_stdout(self.output)
        self.quiet.__enter__()
        self.git = {'rev-parse --abbrev-ref HEAD': 'main\n',
                    'rev-parse --git-path rebase-merge': str(self.root / 'rebase-merge'),
                    'rev-parse --git-path rebase-apply': str(self.root / 'rebase-apply'),
                    STATUS: '',
                    'rev-parse HEAD': 'aaa\n', 'rev-list --count origin/main..HEAD': '0\n'}
        self.remote = done('abc refs/heads/main\n')
        self.runs = []
        self.run_kwargs = []

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def read(self, argv, cwd=None, timeout_s=60, input=None):
        key = ' '.join(map(str, argv[1:]))
        if key.startswith('ls-remote'):
            return self.remote
        value = self.git.get(key, done('', 1, 'not stubbed: ' + key))
        return value if isinstance(value, subprocess.CompletedProcess) else done(value)

    def run_cmd(self, argv, **kwargs):
        if argv[1] == 'pull' and any('D' in xy for xy, _ in sy.parse_porcelain(self.git[STATUS])):
            raise subprocess.CalledProcessError(128, argv)  # real git: unstaged changes block pull --rebase
        self.runs.append([str(a) for a in argv])
        self.run_kwargs.append(kwargs)

    def make(self, *argv):
        setup = m.Setup(m.parser().parse_args(list(argv) or ['--profile', 'linux']), root=self.root)
        setup._class = 'laptop'
        for name, fake in [('find', lambda n: n), ('read', self.read), ('run', self.run_cmd), ('editors', MagicMock(return_value=[]))]:
            setattr(setup, name, fake)
        return sy.Sync(setup, applications=self.root / 'Applications')


class DotfilesTests(Base):
    def test_clean_online_pulls_and_does_not_push(self):
        sync = self.make()
        heads = iter(['aaa\n', 'bbb\n'])
        self.git['rev-parse HEAD'] = None
        sync.setup.read = lambda a, cwd=None, timeout_s=60: done(next(heads)) if a[1:] == ['rev-parse', 'HEAD'] else self.read(a)
        result = sync.dotfiles()
        self.assertEqual(self.runs, [PULL])
        self.assertEqual(result.status, 'changed')

    def test_dirty_commits_tracked_only_pulls_then_pushes(self):
        sync = self.make()
        self.git[STATUS] = ' M a b.txt\0 M c\0'
        self.git['rev-list --count origin/main..HEAD'] = '1\n'
        result = sync.dotfiles()
        self.assertEqual([r[1:3] for r in self.runs], [['add', '-u'], ['commit', '-m'], ['pull', '--rebase'], ['push', 'origin']])
        self.assertEqual(self.runs[0], ['yadm', 'add', '-u', '--', 'a b.txt', 'c'])
        self.assertEqual(self.runs[1][-3:], ['--', 'a b.txt', 'c'])
        self.assertNotIn('-A', self.runs[0])
        for kwargs in self.run_kwargs[:2]:
            self.assertEqual(kwargs['cwd'], self.root)
            self.assertEqual(kwargs['env']['GIT_LITERAL_PATHSPECS'], '1')
        self.assertIn('2 files', self.runs[1][3])
        self.assertEqual((result.status, result.details), ('changed', ['a b.txt', 'c']))
        sync.setup.editors.assert_called_once()

    def test_conflict_aborts_rebase_and_fails(self):
        sync = self.make()
        sync.setup.args.plan = False
        def run(argv, **kwargs):
            self.runs.append([str(a) for a in argv])
            if argv[1] == 'pull':
                (self.root / 'rebase-merge').mkdir()
                raise subprocess.CalledProcessError(1, argv)
        sync.setup.run = run
        with patch.object(sy, 'PHASES', [('dotfiles', 'Dotfiles')]):
            self.assertEqual(sync.execute(), 1)
        self.assertIn(['yadm', 'rebase', '--abort'], self.runs)
        self.assertFalse(any(r[1] == 'push' for r in self.runs))
        self.assertEqual(sync.results['dotfiles'].status, 'failed')
        self.assertIn('rebase aborted', sync.results['dotfiles'].summary)

    def test_pull_failure_without_rebase_is_reported(self):
        sync = self.make()
        def run(argv, **kwargs):
            raise subprocess.CalledProcessError(1, argv)
        sync.setup.run = run
        with self.assertRaisesRegex(RuntimeError, 'pull failed'):
            sync.dotfiles()

    def test_offline_commits_locally_skips_pull_push(self):
        sync = self.make()
        self.remote = done('', 128, 'fatal: could not resolve host')
        self.git[STATUS] = ' M a\0'
        result = sync.dotfiles()
        self.assertEqual([r[1] for r in self.runs], ['add', 'commit'])
        self.assertEqual(result.status, 'warn')
        self.assertIn('remote unreachable', result.summary)
        self.assertEqual([r[1] for r in self.runs], ['add', 'commit'])

    def test_skips_non_main_branch(self):
        sync = self.make()
        self.git['rev-parse --abbrev-ref HEAD'] = 'feat/sync\n'
        result = sync.dotfiles()
        self.assertEqual((result.status, self.runs), ('skipped', []))
        self.assertIn('feat/sync', result.summary)

    def test_refuses_when_rebase_in_progress_or_conflicted(self):
        sync = self.make()
        (self.root / 'rebase-apply').mkdir()
        with self.assertRaisesRegex(RuntimeError, 'rebase in progress'):
            sync.dotfiles()
        (self.root / 'rebase-apply').rmdir()
        self.git[STATUS] = 'UU conflicted\0'
        with self.assertRaisesRegex(RuntimeError, 'unresolved conflict'):
            sync.dotfiles()
        self.assertEqual(self.runs, [])

    def test_deletions_commit_others_then_pause_pull_and_push(self):
        sync = self.make()
        self.git[STATUS] = ' D gone\0 M a\0D  staged-gone\0'
        result = sync.dotfiles()
        self.assertEqual([r[1] for r in self.runs], ['add', 'commit'])
        self.assertEqual(self.runs[0], ['yadm', 'add', '-u', '--', 'a'])
        self.assertEqual(self.runs[1][-2:], ['--', 'a'])
        self.assertEqual(result.status, 'warn')
        self.assertIn('2 tracked files deleted locally; pull/push paused', result.summary)
        self.assertIn('yadm checkout -- <p>', result.summary)
        self.assertIn('yadm checkout HEAD -- <p>', result.summary)
        self.assertIn('deleted locally, not synced: gone', result.details)
        self.assertIn('deleted locally, not synced: staged-gone', result.details)

    def test_only_deletions_runs_nothing_and_keeps_details(self):
        sync = self.make()
        self.git[STATUS] = ' D gone\0'
        result = sync.dotfiles()
        self.assertEqual(self.runs, [])
        self.assertEqual(result.status, 'warn')
        self.assertEqual(result.details, ['deleted locally, not synced: gone'])

    def test_staged_rename_is_refused(self):
        sync = self.make()
        self.git[STATUS] = 'R  new\0old\0'
        with self.assertRaisesRegex(RuntimeError, 'staged rename'):
            sync.dotfiles()
        self.assertEqual(self.runs, [])

    def test_mutating_commands_carry_timeouts(self):
        sync = self.make()
        self.git[STATUS] = ' M a\0'
        self.git['rev-list --count origin/main..HEAD'] = '1\n'
        sync.dotfiles()
        self.assertEqual([k['timeout'] for k in self.run_kwargs], [sy.GIT_TIMEOUT] * 4)

    def test_timeout_is_a_failed_phase(self):
        sync = self.make()
        def run(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
        sync.setup.run = run
        with patch.object(sy, 'PHASES', [('dotfiles', 'Dotfiles')]):
            self.assertEqual(sync.execute(), 1)
        self.assertIn('pull failed', sync.results['dotfiles'].summary)

    def test_push_rejected_after_pull_fails_phase_and_keeps_commits(self):
        sync = self.make()
        self.git['rev-list --count origin/main..HEAD'] = '2\n'
        def run(argv, **kwargs):
            self.runs.append([str(a) for a in argv])
            if argv[1] == 'push':
                raise subprocess.CalledProcessError(1, argv)
        sync.setup.run = run
        with self.assertRaisesRegex(RuntimeError, 'push failed'):
            sync.dotfiles()
        self.assertEqual([r[1] for r in self.runs], ['pull', 'push'])

    def test_missing_remote_branch_is_not_offline(self):
        sync = self.make()
        self.remote = done('', 2)
        result = sync.dotfiles()
        self.assertNotIn('unreachable', result.summary)
        self.assertEqual(self.runs[0][1], 'pull')

    def test_differing_live_editor_settings_are_held_with_warning(self):
        sync = self.make()
        sync.setup.editors = MagicMock(return_value=['/live/settings.json'])
        result = sync.dotfiles()
        sync.setup.editors.assert_called_once_with(protect_live=True)
        self.assertEqual(result.status, 'warn')
        self.assertIn('live settings differ from tracked; reconcile then run dotfiles-setup: /live/settings.json', result.details)

    def test_plan_counts_pending_commit_as_ahead(self):
        sync = self.make('--plan', '--profile', 'linux')
        self.git[STATUS] = ' M a\0'
        sync.dotfiles()
        self.assertIn(['yadm', 'push', 'origin', 'main'], self.runs)


class PureTests(unittest.TestCase):
    def test_parse_porcelain_handles_renames_and_spaces(self):
        z = ' M a b.txt\0R  new.txt\0old.txt\0A  c\0'
        self.assertEqual(sy.parse_porcelain(z), [(' M', 'a b.txt'), ('R ', 'new.txt'), ('A ', 'c')])
        self.assertEqual(sy.parse_porcelain(''), [])

    def test_commit_message_format(self):
        self.assertEqual(sy.commit_message('laptop@h', ['a', 'b']), 'sync(laptop@h): 2 files\n\na\nb')
        self.assertTrue(sy.commit_message('x', ['a']).startswith('sync(x): 1 file\n'))
        lines = sy.commit_message('x', ['f%d' % i for i in range(30)]).splitlines()
        self.assertEqual(lines[-1], '… and 5 more')
        self.assertEqual(len(lines), 2 + 25 + 1)

    def test_count_findings(self):
        out = ('normal       ctrl+a     clash      yazi: open <-> tmux: x\n'
               'tmux prefix  a          layer      nvim: y\n'
               'insert mode  b          clash      z: q\n')
        self.assertEqual(sy.count_findings(out), {'clash': 2, 'layer': 1, 'overridden': 0})


class StateTests(Base):
    def stub_phases(self, failing=None):
        patches = {}
        for method, _ in sy.PHASES:
            if method == failing:
                patches[method] = MagicMock(side_effect=RuntimeError('boom'))
            else:
                patches[method] = MagicMock(return_value=sy.PhaseResult('ok', method + ' fine', ['d']))
        return patch.multiple(sy.Sync, **patches)

    def test_last_json_written_with_all_phases(self):
        sync = self.make()
        with self.stub_phases():
            self.assertEqual(sync.execute(), 0)
        data = json.loads((self.root / sy.STATE_DIR / 'last.json').read_text())
        self.assertEqual(list(data['phases']), [k for k, _ in sy.PHASES])
        self.assertEqual((data['format'], data['exit'], data['profile']), (1, 0, 'linux'))
        self.assertTrue(data['machine'].startswith('laptop@'))
        self.assertEqual(list(data['phases'].values())[0]['details'], ['d'])

    def test_status_prints_last_result_and_missing_file_returns_1(self):
        self.assertEqual(sy.print_status(self.root, False), 1)
        self.assertIn('No sync has run yet', self.output.getvalue())
        with self.stub_phases():
            self.make().execute()
        self.assertEqual(sy.print_status(self.root, True), 0)
        text = self.output.getvalue()
        self.assertIn('Last sync:', text)
        self.assertIn('layout fine', text)
        self.assertIn('Schedule: installed', text)

    def test_status_lists_details_and_fix_hints_under_warn_phases(self):
        phases = {'layout': sy.PhaseResult('warn', 'unplanned 2', ['unplanned:Google Drive', 'unplanned:stray']),
                  'apps': sy.PhaseResult('warn', '1 app', ['Hotkeys absent: build locally']),
                  'doctor': sy.PhaseResult('ok', 'all checks passed', ['hidden'])}
        meta = {'started': 'x', 'finished': datetime.now(timezone.utc).isoformat(), 'machine': 'laptop@h', 'profile': 'linux', 'exit': 1}
        sy.write_state(self.root, phases, meta)
        self.assertEqual(sy.print_status(self.root, True), 1)
        lines = self.output.getvalue().splitlines()
        self.assertIn('      unplanned (2): Google Drive, stray', lines)
        self.assertIn('      fix: ' + sy.HINTS['layout'], lines)
        self.assertIn('      Hotkeys absent: build locally', lines)
        self.assertNotIn('      hidden', lines)
        self.assertEqual(len(sy.format_details(['cask:' + 'x' * 20] * 12)), 3)

    def fake_remote(self, statuses):
        """Stub fetch/for-each-ref/show so the remote holds these last.json dicts."""
        refs = ['refs/remotes/origin/' + sy.status_ref(d['machine']) for d in statuses]
        self.git['fetch --quiet --prune origin +refs/heads/status/*:refs/remotes/origin/status/*'] = ''
        self.git['for-each-ref --format=%(refname) refs/remotes/origin/status/'] = '\n'.join(refs) + '\n'
        for ref, data in zip(refs, statuses):
            self.git['show %s:last.json' % ref] = json.dumps(data)

    @staticmethod
    def status(machine, hours_ago, exit_code=0, phases=None):
        finished = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        return {'machine': machine, 'finished': finished, 'exit': exit_code,
                'phases': phases or {'layout': {'status': 'ok', 'summary': '', 'details': []}}}

    def test_status_ref_is_ref_safe(self):
        self.assertEqual(sy.status_ref("laptop@Joseph\u2019s-MacBook-Pro"), 'status/laptop-Joseph-s-MacBook-Pro')
        self.assertEqual(sy.status_ref('cluster@login.swan'), 'status/cluster-login.swan')

    def test_sync_checks_in_and_warns_about_stale_machines(self):
        sync = self.make()
        self.git.update({'commit-tree t -m status laptop@%s' % sync.machine_label().split('@')[1]: 'c\n', 'mktree': 't\n',
                         'push --force --quiet origin c:refs/heads/' + sy.status_ref(sync.machine_label()): ''})
        self.fake_remote([self.status('studio@studio', 3 * 24), self.status('linux@gpu', 1)])
        with self.stub_phases(), patch.object(sync.setup, 'read_ok', wraps=sync.setup.read_ok) as read_ok:
            self.git['hash-object -w %s' % (self.root / sy.STATE_DIR / 'last.json')] = 'b\n'
            self.assertEqual(sync.execute(), 0)
        self.assertEqual(read_ok.call_args_list[1].kwargs['input'], '100644 blob b\tlast.json\n')
        push = read_ok.call_args_list[3].args[0]
        self.assertEqual(push[:5], ['yadm', 'push', '--force', '--quiet', 'origin'])
        self.assertEqual(push[5], 'c:refs/heads/' + sy.status_ref(sync.machine_label()))
        text = self.output.getvalue()
        self.assertIn('stale: studio@studio has not checked in for 2 days', text)
        self.assertNotIn('linux@gpu has not', text)

    def test_checkin_failure_is_a_note_not_an_error(self):
        sync = self.make()
        with self.stub_phases():
            self.assertEqual(sync.execute(), 0)
        self.assertIn('check-in skipped: hash-object failed', self.output.getvalue())
        sync = self.make('--plan', '--profile', 'linux')
        with self.stub_phases():
            sync.execute()
        self.assertEqual(self.output.getvalue().count('check-in skipped'), 1)

    def test_fleet_lists_every_checkin_newest_first_and_missing_classes(self):
        fleet = self.root / 'fleet.txt'
        fleet.write_text('# expected\nlaptop\nstudio\nlinux\ncluster\n')
        failed = {'dotfiles': {'status': 'failed', 'summary': 'x', 'details': []},
                  'doctor': {'status': 'warn', 'summary': 'y', 'details': []},
                  'apps': {'status': 'ok', 'summary': '', 'details': []}}
        self.fake_remote([self.status('studio@studio', 60, 1, failed), self.status('laptop@book', 2)])
        sync = self.make()
        self.assertEqual(sy.fleet(sync.setup, fleet), 1)
        lines = self.output.getvalue().splitlines()
        self.assertEqual(lines[0].split(), ['book', 'laptop', '2h', 'ago', 'exit', '0'])
        self.assertEqual(lines[1].split(), ['studio', 'studio', '2d', 'ago', 'exit', '1', 'dotfiles:failed', 'doctor:warn'])
        self.assertEqual([l.split() for l in lines[2:4]], [['?', 'linux', 'never'], ['?', 'cluster', 'never']])
        self.assertEqual(lines[4], 'stale: studio@studio has not checked in for 2 days')
        self.assertEqual(len(lines), 5)

    def test_fleet_checkin_publishes_first_and_is_clean_when_all_ok(self):
        fleet = self.root / 'fleet.txt'
        fleet.write_text('laptop\n')
        with self.stub_phases():
            self.make().execute()
        sync = self.make()
        self.git.update({'hash-object -w %s' % (self.root / sy.STATE_DIR / 'last.json'): 'b\n', 'mktree': 't\n',
                         'commit-tree t -m status ' + sync.machine_label(): 'c\n',
                         'push --force --quiet origin c:refs/heads/' + sy.status_ref(sync.machine_label()): ''})
        self.fake_remote([self.status('laptop@book', 5)])
        with patch.object(sync.setup, 'read', wraps=sync.setup.read) as read:
            self.assertEqual(sy.fleet(sync.setup, fleet, checkin=True), 0)
        self.assertEqual(read.call_args_list[3].args[0][1:3], ['push', '--force'])
        self.assertEqual(self.output.getvalue().splitlines()[-1].split()[:2], ['book', 'laptop'])

    def test_fleet_offline_fetch_is_an_error(self):
        self.git['fetch --quiet --prune origin +refs/heads/status/*:refs/remotes/origin/status/*'] = done('', 128, 'fatal: unable to access')
        with self.assertRaises(RuntimeError) as caught:
            sy.fleet(self.make().setup, self.root / 'fleet.txt')
        self.assertIn('fetch failed: fatal: unable to access', str(caught.exception))

    def test_failed_phase_does_not_stop_later_phases(self):
        sync = self.make()
        with self.stub_phases(failing='dotfiles'):
            self.assertEqual(sync.execute(), 1)
        self.assertEqual(sync.results['dotfiles'].status, 'failed')
        self.assertEqual(sync.results['doctor'].status, 'ok')
        self.assertEqual(len(sync.results), len(sy.PHASES))

    def test_unexpected_exception_type_is_failed_phase_and_state_still_written(self):
        sync = self.make()
        with self.stub_phases(), patch.object(sy.Sync, 'repos', MagicMock(side_effect=KeyError('x'))):
            self.assertEqual(sync.execute(), 1)
        self.assertEqual(sync.results['repos'].status, 'failed')
        self.assertIn('KeyError', sync.results['repos'].summary)
        self.assertEqual(sync.results['doctor'].status, 'ok')
        data = json.loads((self.root / sy.STATE_DIR / 'last.json').read_text())
        self.assertEqual(data['exit'], 1)

    def test_interrupt_still_writes_state(self):
        sync = self.make()
        with self.stub_phases(), patch.object(sy.Sync, 'repos', MagicMock(side_effect=KeyboardInterrupt)):
            with self.assertRaises(KeyboardInterrupt):
                sync.execute()
        data = json.loads((self.root / sy.STATE_DIR / 'last.json').read_text())
        self.assertEqual((data['exit'], list(data['phases'])[-1]), (1, 'packages'))

    def test_failed_state_write_leaves_no_temp_file(self):
        directory = self.root / sy.STATE_DIR
        with patch.object(sy.json, 'dump', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                sy.write_state(self.root, {}, {})
        self.assertEqual(list(directory.iterdir()), [])

    def test_lock_held_returns_1(self):
        held = sy.acquire_lock(self.root / sy.STATE_DIR / 'lock')
        self.assertIsNotNone(held)
        try:
            with self.stub_phases():
                self.assertEqual(self.make().execute(), 1)
        finally:
            held.close()
        self.assertIn('another sync is running', self.output.getvalue())
        self.assertFalse((self.root / sy.STATE_DIR / 'last.json').exists())


class PhaseTests(Base):
    def test_hotkeys_counts_and_warns_on_clash(self):
        sync = self.make('--profile', 'mac')
        script = self.root / 'local/code/web/hotkeys/scripts/check.js'
        script.parent.mkdir(parents=True)
        script.write_text('')
        sync.setup.read = lambda a, cwd=None, timeout_s=60: done('n  a  layer  s: x\nn  b  clash  s: y\n')
        result = sync.hotkeys()
        self.assertEqual((result.status, result.summary), ('warn', '1 clashes, 1 layer overlaps'))

    def test_repos_skipped_without_grc_and_runs_with_it(self):
        sync = self.make()
        sync.setup.find = lambda n: None
        self.assertEqual(sync.repos().status, 'skipped')
        config = self.root / '.config/git-repo-checker/active.yml'
        config.parent.mkdir(parents=True)
        config.write_text('')
        sync.setup.find = lambda n: 'grc'
        self.assertEqual(sync.repos().status, 'ok')
        self.assertEqual(self.runs[0][:4], ['grc', 'active', 'sync', '--apply'])

    def search_checkout(self, sync):
        checkout = sync.setup.checkout('s')
        checkout.mkdir(parents=True, exist_ok=True)
        (checkout / 'pyproject.toml').write_text('[project]\nname = "search-cli"\n')
        return checkout

    def test_repos_reinstalls_s_when_missing_then_leaves_it_alone(self):
        sync = self.make()
        self.search_checkout(sync)
        present = {'grc', 'uv'}
        sync.setup.find = lambda n: n if n in present else None
        with patch.object(sync.setup, 'tool') as tool:
            result = sync.repos()
            self.assertEqual(result.status, 'changed')
            self.assertIn('s reinstalled', result.summary)
            tool.assert_called_once_with('s')
            marker = self.root / sy.STATE_DIR / 'search-cli.sha256'
            self.assertEqual(marker.read_text().strip(), sy.checkout_digest(sync.setup.checkout('s'), sync.setup.extras('s')))
            self.assertNotEqual(sy.checkout_digest(sync.setup.checkout('s')), marker.read_text().strip())  # extras are part of the digest
            present.add('s')
            self.assertEqual(sync.repos().status, 'skipped')
            tool.assert_called_once()

    def test_repos_reinstalls_s_when_dependencies_change(self):
        sync = self.make()
        checkout = self.search_checkout(sync)
        with patch.object(sync.setup, 'tool') as tool:
            sync.repos()
            (checkout / 'uv.lock').write_text('version = 1\n')
            sync.repos()
            self.assertEqual(tool.call_count, 2)
            self.assertIn('s up to date', sync.repos().summary)
            self.assertEqual(tool.call_count, 2)

    def test_repos_search_skips_without_checkout_or_uv_and_in_plan(self):
        sync = self.make()
        with patch.object(sync.setup, 'tool', side_effect=AssertionError('installed')):
            self.assertIn('checkout absent', sync.repos().summary)
            self.search_checkout(sync)
            sync.setup.find = lambda n: None if n == 'uv' else n
            self.assertIn('uv missing', sync.repos().summary)
        plan = self.make('--plan', '--profile', 'linux')
        self.search_checkout(plan)
        with patch.object(plan.setup, 'tool') as tool:
            self.assertIn('would be reinstalled', plan.repos().summary)
        tool.assert_called_once_with('s')
        self.assertFalse((self.root / sy.STATE_DIR / 'search-cli.sha256').exists())

    def grc_checkout(self, sync):
        checkout = sync.setup.checkout('grc')
        (checkout / '.git').mkdir(parents=True)
        (checkout / 'pyproject.toml').write_text('[project]\nname = "git-repo-checker"\n')
        return checkout

    def test_repos_fast_forwards_and_reinstalls_grc_before_using_it(self):
        sync = self.make()
        grc = self.grc_checkout(sync)
        config = self.root / '.config/git-repo-checker/active.yml'
        config.parent.mkdir(parents=True)
        config.write_text('')
        present = {'uv'}
        sync.setup.find = lambda n: n if n in present else None
        with patch.object(sync.setup, 'tool', side_effect=present.add) as tool:
            result = sync.repos()
        self.assertEqual(self.runs[0], ['git', '-C', str(grc), 'pull', '--ff-only', '--quiet'])
        tool.assert_called_once_with('grc')
        self.assertEqual(self.runs[1][:4], ['grc', 'active', 'sync', '--apply'])
        self.assertEqual(result.status, 'changed')
        self.assertIn('grc reinstalled', result.summary)
        self.assertTrue((self.root / sy.STATE_DIR / 'git-repo-checker.sha256').exists())

    def test_repos_failed_grc_sync_still_refreshes_s_and_fails_the_phase(self):
        sync = self.make()
        self.search_checkout(sync)
        config = self.root / '.config/git-repo-checker/active.yml'
        config.parent.mkdir(parents=True)
        config.write_text('')
        real = sync.setup.run

        def run(argv, **kwargs):
            if argv[1] == 'active':
                raise subprocess.CalledProcessError(2, argv)
            real(argv, **kwargs)
        sync.setup.run = run
        with patch.object(sync.setup, 'tool') as tool:
            result = sync.repos()
        tool.assert_called_once_with('s')
        self.assertEqual(result.status, 'failed')
        self.assertIn('grc active sync failed', result.summary)
        self.assertIn('s reinstalled', result.summary)

    def test_repos_reports_a_failed_grc_fast_forward_and_carries_on(self):
        sync = self.make()
        self.grc_checkout(sync)
        real = sync.setup.run

        def run(argv, **kwargs):
            if argv[0] == 'git':
                raise subprocess.CalledProcessError(128, argv)
            real(argv, **kwargs)
        sync.setup.run = run
        with patch.object(sync.setup, 'tool'):
            result = sync.repos()
        self.assertIn('not fast-forwarded', result.summary)
        self.assertIn('grc reinstalled', result.summary)  # the failed pull did not stop the phase

    def test_packages_honours_skip_packages(self):
        sync = self.make('--profile', 'mac', '--skip-packages')
        with patch.object(sync.setup, 'linux_tools', side_effect=AssertionError('installed')):
            self.assertEqual(sync.packages().status, 'skipped')
        linux = self.make('--profile', 'linux', '--skip-packages')
        self.assertEqual(linux.packages().status, 'skipped')

    def test_doctor_counts_absolute_paths(self):
        sync = self.make()
        sync.setup.doctor = lambda: ['x missing', 'Absolute home path: a:1']
        result = sync.doctor()
        self.assertEqual((result.status, result.summary), ('warn', '2 items need attention, 1 absolute home paths'))


class PlanTests(Base):
    def fake_read(self, argv, cwd=None, timeout_s=60):
        name = Path(str(argv[0])).name
        key = ' '.join(map(str, argv[1:]))
        if name == 'yadm':
            return self.remote if key.startswith('ls-remote') else done(self.git.get(key, 'laptop\n'))
        answers = {'list': done(''), 'leaves': done(''), 'info': done('{"casks":[]}')}
        if name == 'brew':
            return answers[str(argv[1])]
        return {'gh': done('v0.2.1\n'), 'pgrep': done('', 1)}.get(name, done(''))

    def seed(self):
        for rel, text in [('.config/git-repo-checker/active.yml', ''), ('local/code/web/hotkeys/scripts/check.js', '')]:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text)
        snapshot = self.root / '.config/yadm/macos/preferences.plist'
        snapshot.parent.mkdir(parents=True)
        snapshot.write_bytes(plistlib.dumps({}))

    def tree(self):
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))

    def test_sync_plan_is_read_only_for_all_profiles(self):
        self.seed()
        before = self.tree()
        for profile in ['mac', 'linux', 'cluster']:
            sync = self.make('--sync', '--plan', '--profile', profile)
            sync.setup.read = self.fake_read
            sync.setup.run = m.Setup.run.__get__(sync.setup)
            sync.setup.editors = m.Setup.editors.__get__(sync.setup)
            sync.setup.doctor = lambda: []
            stub = MagicMock(apply=MagicMock(return_value=2))
            self.output.truncate(0)
            self.output.seek(0)
            with patch.object(m.subprocess, 'run', side_effect=AssertionError('ran')), patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('net')), \
                    patch('shutil.move', side_effect=AssertionError('moved')), patch.object(sy, 'load_mac_settings', return_value=stub):
                self.assertEqual(sync.execute(), 0, self.output.getvalue())
            summary = self.output.getvalue().split('Summary\n')[1].splitlines()
            self.assertTrue(summary[0].split()[0] == 'layout')
            self.assertEqual(self.tree(), before)
            if profile == 'mac':
                self.assertEqual(sync.results['defaults'].summary, '2 would change')
                self.assertEqual(sync.results['hotkeys'].status, 'ok')


if __name__ == '__main__':
    unittest.main()
