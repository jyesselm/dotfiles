"""converge sync: converge this machine daily and record per-phase results."""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import platform
import plistlib
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

STATE_DIR = '.local/state/dotfiles/sync'
PHASES = [('layout', 'Directory layout'),
          ('dotfiles', 'Dotfiles (yadm)'),
          ('packages', 'Packages'),
          ('repos', 'Repositories (grc)'),
          ('apps', 'Home-made apps'),
          ('defaults', 'Mac defaults'),
          ('hotkeys', 'Hotkey clash check'),
          ('doctor', 'Doctor')]
SELF_PRINTING = {'layout', 'doctor'}  # these phases already print their own detail lines
GIT_TIMEOUT, BREW_TIMEOUT, NET_TIMEOUT = 300, 1800, 600  # seconds, for mutating subprocesses
GRC_FALLBACK = 'micromamba/envs/py3/bin/grc'
HINTS = {  # printed by --status under a warn/failed phase: how to clear it
    'layout': 'move stray entries out of ~, or add "<glob>  ignore" to setup/layout.txt for folders another program owns',
    'packages': 'add packages wanted everywhere to a Brewfile; allow the rest on this computer with converge adopt-extras',
    'dotfiles': 'yadm status, then yadm pull --rebase origin main',
    'repos': 'fix the repo named above, then converge sync',
    'doctor': 'converge doctor reruns the checks',
}
GLYPHS = {'ok': ('✓', '32'), 'changed': ('✓', '36'), 'skipped': ('-', '2'), 'warn': ('!', '33'), 'failed': ('✗', '31')}  # calm first
DETAIL_LIMIT = 12  # detail lines per group in converge status; --all lifts it
STATUS_REFS, STALE_DAYS = 'status/', 2  # each machine force-pushes its last.json to status/<class>-<host>


@dataclass
class PhaseResult:
    """Outcome of one sync phase; status is ok|changed|warn|skipped|failed."""
    status: str
    summary: str
    details: List[str] = field(default_factory=list)


def parse_porcelain(z: str) -> List[Tuple[str, str]]:
    """(XY, path) pairs from `status --porcelain=v1 -z`; rename/copy entries consume the extra field."""
    fields = z.split('\0')
    entries = []
    i = 0
    while i < len(fields):
        item = fields[i]
        i += 1
        if len(item) < 4:
            continue
        entries.append((item[:2], item[3:]))
        if item[0] in 'RC' or item[1] in 'RC':
            i += 1
    return entries


def commit_message(label: str, files: List[str]) -> str:
    """Subject plus at most 25 listed paths."""
    noun = 'file' if len(files) == 1 else 'files'
    body = list(files[:25])
    if len(files) > 25:
        body.append('… and %d more' % (len(files) - 25))
    return 'sync(%s): %d %s\n\n%s' % (label, len(files), noun, '\n'.join(body))


def count_findings(stdout: str) -> Dict[str, int]:
    """Count clash/layer/overridden lines from hotkeys scripts/check.js."""
    counts = {'clash': 0, 'layer': 0, 'overridden': 0}
    for line in stdout.splitlines():
        found = re.search(r'\s(clash|layer|overridden)\s', line)
        if found:
            counts[found.group(1)] += 1
    return counts


def load_mac_settings(path: Path):
    """Import mac-settings.py (its name has a hyphen)."""
    spec = importlib.util.spec_from_file_location('mac_settings', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checkout_digest(checkout: Path, extras: str = '') -> str:
    """sha256 over pyproject.toml, uv.lock and the installed extras; <repo>.sha256 under STATE_DIR records the last install."""
    digest = hashlib.sha256(extras.encode())
    for name in ('pyproject.toml', 'uv.lock'):
        if (checkout / name).exists():
            digest.update(name.encode() + b'\0' + (checkout / name).read_bytes())
    return digest.hexdigest()


def acquire_lock(path: Path):
    """Exclusive non-blocking flock; returns the open file, or None if already held."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, 'w')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def format_results(phases: Dict[str, PhaseResult]) -> List[str]:
    """Aligned 'key status summary' lines."""
    return ['  %-9s %-8s %s' % (key, r.status, r.summary) for key, r in phases.items()]


def write_state(root: Path, phases: Dict[str, PhaseResult], meta: dict) -> Path:
    """Atomically write last.json; a failed write leaves no temp file behind."""
    directory = Path(root) / STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    data = dict(meta, format=1, phases={k: asdict(v) for k, v in phases.items()})
    target = directory / 'last.json'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=directory, delete=False, suffix='.tmp') as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2)
        temporary.replace(target)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    return target


def paint(text: str, code: str, color: bool) -> str:
    return '\033[%sm%s\033[0m' % (code, text) if color else text


def tilde(text: str, root) -> str:
    """Shorten this home directory to ~ in printed text."""
    return text.replace(str(root), '~')


def format_details(details: List[str], limit=None, width: int = 100, indent: str = '    ') -> Tuple[List[str], bool]:
    """(Indented detail lines, whether any were cut): 'key:value' details are grouped as 'key (n): a, b, c', wrapped, capped at `limit` each."""
    groups: Dict[str, List[str]] = {}
    plain = []
    for detail in details:
        match = re.match(r'^([a-z-]+):(\S.*)$', detail)
        if match:
            groups.setdefault(match.group(1), []).append(match.group(2))
        else:
            plain.append(detail)
    lines, cut = [], False
    for key, values in groups.items():
        shown = values if limit is None else values[:limit]
        cut |= len(shown) < len(values)
        head = '%s%s (%s): ' % (indent, key, len(values) if len(shown) == len(values) else '%d of %d' % (len(shown), len(values)))
        lines += textwrap.wrap(', '.join(shown) + (', …' if len(shown) < len(values) else ''), width, initial_indent=head,
                               subsequent_indent=' ' * len(head), break_long_words=False, break_on_hyphens=False)
    shown = plain if limit is None else plain[:limit]
    lines += [indent + d for d in shown]
    if len(shown) < len(plain):
        cut = True
        lines.append('%s… %d more' % (indent, len(plain) - len(shown)))
    return lines, cut


def print_status(root: Path, schedule_installed: bool, show_all: bool = False) -> int:
    """Print the last sync: phases with problems last, then each problem's details and how to clear it. Returns its exit code."""
    path = Path(root) / STATE_DIR / 'last.json'
    if not path.exists():
        print('No sync has run yet; try converge sync --plan')
        return 1
    data = json.loads(path.read_text())
    color = sys.stdout.isatty() and not os.environ.get('NO_COLOR')
    phases = {k: PhaseResult(**v) for k, v in data['phases'].items()}
    when = datetime.fromisoformat(data['finished']).astimezone().strftime('%a %H:%M')
    print('Last sync %s (%s) · %s · exit %d · schedule %s\n' % (
        age(data['finished']), when, data['machine'], data['exit'], 'installed' if schedule_installed else 'not installed'))
    for key, result in sorted(phases.items(), key=lambda kv: list(GLYPHS).index(kv[1].status)):
        glyph, code = GLYPHS[result.status]
        lines = textwrap.wrap(tilde(result.summary, root), 110, initial_indent='  %s %-9s ' % (glyph, key), subsequent_indent=' ' * 14)
        lines[0] = lines[0].replace(glyph, paint(glyph, code, color), 1)
        print('\n'.join(lines))
    problems = sorted(((k, r) for k, r in phases.items() if r.status in ('warn', 'failed')), key=lambda kv: kv[1].status != 'failed')
    if problems:
        print('\n' + paint('Needs attention', '1', color))
    cut = False
    for key, result in problems:
        print('\n  %s  %s' % (paint(key, GLYPHS[result.status][1], color), tilde(result.summary, root)))
        lines, cut_here = format_details([tilde(d, root) for d in result.details], None if show_all else DETAIL_LIMIT)
        cut |= cut_here
        print('\n'.join(lines + textwrap.wrap(HINTS[key], 110, initial_indent='    fix: ', subsequent_indent=' ' * 9) if key in HINTS else lines))
    if cut:
        print('\n  Full lists: converge status --all')
    return int(data['exit'])


def age(finished: str) -> str:
    """'3h ago' under two days, else '8d ago'."""
    hours = (datetime.now(timezone.utc) - datetime.fromisoformat(finished)).total_seconds() / 3600
    return '%dh ago' % hours if hours < 48 else '%dd ago' % (hours / 24)


def status_ref(machine: str) -> str:
    """Branch that holds a machine's last.json: status/<class>-<host>, ref-safe."""
    return STATUS_REFS + re.sub(r'[^A-Za-z0-9.-]+', '-', machine).strip('-')


def publish_status(setup, yadm: str) -> None:
    """Force-push last.json as a single parentless commit to this machine's status branch."""
    path = setup.root / STATE_DIR / 'last.json'
    machine = json.loads(path.read_text())['machine']
    blob = setup.read_ok([yadm, 'hash-object', '-w', path], 'hash-object failed').strip()
    tree = setup.read_ok([yadm, 'mktree'], 'mktree failed', input='100644 blob %s\tlast.json\n' % blob).strip()
    commit = setup.read_ok([yadm, 'commit-tree', tree, '-m', 'status ' + machine], 'commit-tree failed').strip()
    setup.read_ok([yadm, 'push', '--force', '--quiet', 'origin', '%s:refs/heads/%s' % (commit, status_ref(machine))],
                  'push failed', timeout_s=GIT_TIMEOUT)  # read_ok: GitHub's pull-request hint stays out of the summary


def fetch_statuses(setup, yadm: str) -> List[dict]:
    """Fetch every status/* branch and return their last.json contents, newest check-in first."""
    spec = '+refs/heads/%s*:refs/remotes/origin/%s*' % (STATUS_REFS, STATUS_REFS)
    fetched = setup.read([yadm, 'fetch', '--quiet', '--prune', 'origin', spec], timeout_s=60)
    if fetched.returncode:
        raise RuntimeError('fetch failed: ' + (fetched.stderr.strip().splitlines() or ['no reply'])[-1])
    refs = setup.read_ok([yadm, 'for-each-ref', '--format=%(refname)', 'refs/remotes/origin/' + STATUS_REFS],
                         'for-each-ref failed').split()
    statuses = [json.loads(setup.read_ok([yadm, 'show', ref + ':last.json'], 'show failed')) for ref in refs]
    return sorted(statuses, key=lambda d: d['finished'], reverse=True)


def stale(statuses: List[dict], days: int = STALE_DAYS) -> List[str]:
    """Machines whose last check-in is older than `days`."""
    limit = datetime.now(timezone.utc) - timedelta(days=days)
    return [d['machine'] for d in statuses if datetime.fromisoformat(d['finished']) < limit]


def fleet(setup, expected: Path, checkin: bool = False) -> int:
    """One line per machine that ever checked in, plus never-seen classes from fleet.txt; 1 unless all clean."""
    yadm = setup.find('yadm')
    if not yadm:
        raise RuntimeError('yadm not on PATH')
    if checkin and setup.args.plan:
        setup.say('plan: check-in not pushed')
    elif checkin:
        publish_status(setup, yadm)
    statuses = fetch_statuses(setup, yadm)
    code = 0
    for data in statuses:
        cls, host = data['machine'].split('@', 1)
        bad = ' '.join('%s:%s' % (k, v['status']) for k, v in data['phases'].items() if v['status'] != 'ok')
        setup.say('%-22s %-8s %-8s exit %-3d %s' % (host, cls, age(data['finished']), data['exit'], bad))
        code |= int(data['exit'] != 0)
    seen = {d['machine'].split('@', 1)[0] for d in statuses}
    classes = [line.split('#')[0].strip() for line in expected.read_text().splitlines()]
    for cls in filter(None, classes):
        if cls not in seen:
            setup.say('%-22s %-8s never' % ('?', cls))
            code = 1
    for machine in stale(statuses):
        setup.say('stale: %s has not checked in for %d days' % (machine, STALE_DAYS))
        code = 1
    return code


class Sync:
    """Runs the sync phases in order against a Setup instance."""

    def __init__(self, setup, applications: Path = Path('/Applications')):
        self.setup = setup
        self.root = setup.root
        self.applications = Path(applications)
        self.results: Dict[str, PhaseResult] = {}

    def machine_label(self) -> str:
        """class@host, used in commit messages and the state file."""
        return '%s@%s' % (self.setup.machine_class(), platform.node().split('.')[0])

    def step(self, key: str, title: str, action) -> None:
        """Run one phase; any exception becomes a failed result and later phases still run."""
        try:
            result = self.setup.phase(title, action)
            if result is None:
                result = PhaseResult('failed', self.setup.errors[-1])
        except Exception as exc:  # unexpected types must not abort the whole sync
            result = PhaseResult('failed', '%s: %s' % (type(exc).__name__, exc))
        self.results[key] = result
        for line in ([] if key in SELF_PRINTING else result.details[:30]):
            self.setup.say('  ' + line)
        self.setup.say('  => %s: %s' % (result.status, result.summary))

    def _run_phases(self) -> int:
        """Run all phases, print the summary; returns 1 if any phase failed."""
        for key, title in PHASES:
            self.step(key, title, getattr(self, key))
        self.setup.say('\nSummary')
        for line in format_results(self.results):
            self.setup.say(line)
        return int(any(r.status == 'failed' for r in self.results.values()))

    def _save(self, started: datetime, code: int) -> None:
        """Record this run in last.json."""
        meta = {'started': started.isoformat(), 'finished': datetime.now(timezone.utc).isoformat(),
                'machine': self.machine_label(), 'profile': self.setup.profile, 'exit': code}
        write_state(self.root, self.results, meta)

    def execute(self) -> int:
        """Run every phase; returns 1 if any failed or another sync holds the lock."""
        plan = self.setup.args.plan
        started = datetime.now(timezone.utc)
        label = '%s/%s' % (self.setup.profile, self.setup.machine_class())
        self.setup.say(('SYNC PLAN' if plan else 'DOTFILES SYNC') + ' — ' + label)
        lock = None if plan else acquire_lock(self.root / STATE_DIR / 'lock')
        if not plan and lock is None:
            self.setup.say('another sync is running')
            return 1
        code = 1  # stays 1 if interrupted
        try:
            code = self._run_phases()
        finally:
            if not plan:
                self._save(started, code)
            if lock is not None:
                lock.close()
        if not plan:
            self.checkin()
        return code

    def checkin(self) -> None:
        """Publish this run and warn about machines that have gone quiet; never changes the exit code."""
        try:
            yadm = self.setup.find('yadm')
            if not yadm:
                raise RuntimeError('yadm not on PATH')
            publish_status(self.setup, yadm)
            for machine in stale(fetch_statuses(self.setup, yadm)):
                self.setup.say('  stale: %s has not checked in for %d days' % (machine, STALE_DAYS))
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self.setup.say('  check-in skipped: %s' % exc)

    def layout(self) -> PhaseResult:
        """Create missing directories; warn about expected-but-absent and unplanned entries."""
        report = self.setup.layout()
        details = (['created:' + p for p in report.created] + ['expected:' + p for p in report.expected]
                   + ['unplanned:' + p for p in report.unplanned])
        if report.created:
            status = 'changed'
        elif report.expected or report.unplanned:
            status = 'warn'
        else:
            status = 'ok'
        counts = [('%d created', report.created), ('%d expected dirs missing', report.expected), ('%d unplanned entries in ~', report.unplanned)]
        summary = ', '.join(label % len(items) for label, items in counts if items) or 'every directory present'
        return PhaseResult(status, summary, details)

    def _yadm(self, yadm: str, *args: str, timeout_s: int = 60) -> str:
        """stdout of a read-only yadm command; RuntimeError on failure."""
        return self.setup.read_ok([yadm, *args], 'yadm ' + args[0] + ' failed', timeout_s=timeout_s)

    def _rebasing(self, yadm: str) -> bool:
        """True while a rebase is in progress in the yadm repo."""
        for name in ('rebase-merge', 'rebase-apply'):
            if Path(self._yadm(yadm, 'rev-parse', '--git-path', name).strip()).exists():
                return True
        return False

    def _dirty_files(self, yadm: str) -> Tuple[List[str], List[str]]:
        """(modified tracked files, locally deleted files); refuses unresolved conflicts."""
        z = self._yadm(yadm, 'status', '--porcelain=v1', '-z', '--untracked-files=no')
        changed, deleted = [], []
        for xy, path in parse_porcelain(z):
            if 'U' in xy or xy in ('AA', 'DD'):
                raise RuntimeError('unresolved conflict in ' + path)
            if xy[0] in 'RC':
                raise RuntimeError('staged rename/copy of %s; commit it yourself with: yadm commit' % path)
            (deleted if 'D' in xy else changed).append(path)
        return changed, deleted

    def _pull_rebase(self, yadm: str) -> None:
        """Rebase onto origin/main; on conflict abort the rebase and keep local commits."""
        try:
            self.setup.run([yadm, 'pull', '--rebase', '--no-autostash', 'origin', 'main'], timeout=GIT_TIMEOUT)
        except subprocess.SubprocessError as exc:
            if not self._rebasing(yadm):
                raise RuntimeError('pull failed (%s); see output above' % exc)
            self.setup.run([yadm, 'rebase', '--abort'], timeout=GIT_TIMEOUT)
            raise RuntimeError('pull conflict: rebase aborted; local commits kept; '
                               'resolve with: yadm pull --rebase origin main')

    def _push_if_ahead(self, yadm: str, dirty: bool) -> bool:
        """Push main when local commits are ahead; plan mode counts the pending commit."""
        ahead = int(self._yadm(yadm, 'rev-list', '--count', 'origin/main..HEAD').strip() or 0)
        if self.setup.args.plan and dirty:
            ahead += 1
        if ahead > 0:
            try:
                self.setup.run([yadm, 'push', 'origin', 'main'], timeout=GIT_TIMEOUT)
            except subprocess.SubprocessError as exc:
                raise RuntimeError('push failed (%s); local commits kept, rerun after fixing' % exc)
        return ahead > 0

    def _commit(self, yadm: str, files: List[str]) -> None:
        """Commit exactly these tracked files. Paths are repo-root relative, so run from the root, literally."""
        opts = {'cwd': self.root, 'env': dict(self.setup.env, GIT_LITERAL_PATHSPECS='1'), 'timeout': GIT_TIMEOUT}
        self.setup.run([yadm, 'add', '-u', '--'] + files, **opts)
        message = commit_message(self.machine_label(), files)
        self.setup.run([yadm, 'commit', '-m', message, '--'] + files, **opts)

    def _pull_and_push(self, yadm: str, dirty: bool) -> Tuple[bool, bool]:
        """Pull --rebase then push; returns (pulled new commits, pushed)."""
        before = self._yadm(yadm, 'rev-parse', 'HEAD')
        self._pull_rebase(yadm)
        pulled = before != self._yadm(yadm, 'rev-parse', 'HEAD')
        return pulled, self._push_if_ahead(yadm, dirty)

    def _remote_reachable(self, yadm: str) -> Tuple[bool, str]:
        """(reachable, reason). ls-remote exit 2 means the branch is missing, not offline."""
        probe = self.setup.read([yadm, 'ls-remote', '--exit-code', '--heads', 'origin', 'main'], timeout_s=20)
        why = (probe.stderr.strip().splitlines() or ['no reply'])[0]
        return probe.returncode in (0, 2), why

    @staticmethod
    def _paused_summary(deleted: List[str]) -> str:
        """Explain why pull/push are paused and how to resolve it."""
        text = ('%d tracked files deleted locally; pull/push paused. Restore with `yadm checkout -- <p>` '
                '(staged: `yadm checkout HEAD -- <p>`) or delete everywhere with `yadm rm <p> && yadm commit`.')
        return text % len(deleted)

    def dotfiles(self) -> PhaseResult:
        """Commit tracked changes, pull --rebase, push, then relink unmodified editor settings."""
        yadm = self.setup.find('yadm')
        if not yadm:
            raise RuntimeError('yadm not on PATH')
        branch = self._yadm(yadm, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
        if branch != 'main':
            return PhaseResult('skipped', 'on branch %s; sync only commits/pushes main' % branch)
        if self._rebasing(yadm):
            raise RuntimeError('rebase in progress; finish or abort it first')
        files, deleted = self._dirty_files(yadm)
        online, why = self._remote_reachable(yadm)
        if files:
            self._commit(yadm, files)
        # Unstaged deletions would make `pull --rebase` fail, so pull/push pause until they are resolved.
        pulled, pushed = self._pull_and_push(yadm, bool(files)) if online and not deleted else (False, False)
        held = self.setup.editors(protect_live=True)
        details = files + ['deleted locally, not synced: ' + p for p in deleted]
        details += ['live settings differ from tracked; reconcile then run converge setup: ' + p for p in held]
        if not online:
            summary = 'remote unreachable (%s): committed %d files locally; pull/push skipped' % (why, len(files))
            return PhaseResult('warn', summary, details)
        if deleted:
            return PhaseResult('warn', self._paused_summary(deleted), details)
        status = 'changed' if (files or pulled or pushed) else 'ok'
        if held:
            status = 'warn'
        done = (['committed %d' % len(files)] if files else []) + (['pulled'] if pulled else []) + (['pushed'] if pushed else [])
        return PhaseResult(status, ', '.join(done) or 'nothing to commit, up to date with origin', details)

    def packages(self) -> PhaseResult:
        """Brewfiles on Mac; the dedicated tool environment elsewhere."""
        if self.setup.args.skip_packages:
            return PhaseResult('skipped', 'skipped by request (--skip-packages)')
        if self.setup.profile == 'mac':
            import sync_mac
            return sync_mac.packages(self.setup, self.setup.machine_class(), self.applications)
        self.setup.linux_tools()
        return PhaseResult('ok', 'tool environment matches linux-packages.txt')

    def apps(self) -> PhaseResult:
        """Home-made apps from GitHub releases (Mac)."""
        import sync_mac
        return sync_mac.apps(self.setup, self.setup.machine_class(), self.applications)

    def repos(self) -> PhaseResult:
        """Keep `grc` current from its checkout, clone and fast-forward the listed repos, then keep `s` on its checkout."""
        details = [self._pull_grc_checkout()]
        grc_reinstalled, detail = self._refresh_tool('grc')
        details.append(detail)
        grc = self.setup.find('grc')
        fallback = self.root / GRC_FALLBACK
        grc = grc or (str(fallback) if fallback.exists() else None)
        config = self.root / '.config/git-repo-checker/active.yml'
        if not grc or not config.exists():
            status, summary = 'skipped', 'grc or active.yml missing; repos not synced'
        else:
            try:  # a broken repo sync must not stop `s` from being refreshed below
                self.setup.run([grc, 'active', 'sync', '--apply', '--quiet', '--config', config], timeout=NET_TIMEOUT)
                status, summary = 'ok', 'grc active sync --apply'
            except (OSError, subprocess.SubprocessError) as exc:
                reason = 'exit %d' % exc.returncode if isinstance(exc, subprocess.CalledProcessError) else str(exc)
                status, summary = 'failed', 'grc active sync failed: ' + reason
        s_reinstalled, detail = self._refresh_tool('s')
        details = [d for d in details + [detail] if d]
        if status != 'failed' and (grc_reinstalled or s_reinstalled):
            status = 'changed'
        return PhaseResult(status, summary, details)

    def _pull_grc_checkout(self) -> str:
        """Fast-forward git-repo-checker itself before it syncs the other repos; a failure is reported, not fatal."""
        checkout = self.setup.checkout('grc')
        if not (checkout / '.git').exists():
            return ''
        try:
            self.setup.run(['git', '-C', checkout, 'pull', '--ff-only', '--quiet'], timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            return 'git-repo-checker not fast-forwarded: ' + str(exc)
        return ''

    def _refresh_tool(self, command: str) -> Tuple[bool, str]:
        """Reinstall `command` when it is missing or its checkout's dependencies changed; (reinstalled, detail)."""
        checkout = self.setup.checkout(command)
        if not (checkout / 'pyproject.toml').exists():
            return False, '%s checkout absent; %s left alone' % (checkout.name, command)
        if not self.setup.find('uv'):
            return False, 'uv missing; %s not refreshed' % command
        marker = self.root / STATE_DIR / (checkout.name + '.sha256')
        digest = checkout_digest(checkout, self.setup.extras(command))
        installed = marker.read_text().strip() if marker.exists() else ''
        if self.setup.find(command) and installed == digest:
            return False, '%s up to date with %s' % (command, checkout)
        self.setup.tool(command)
        if self.setup.args.plan:
            return False, '%s would be reinstalled from %s' % (command, checkout)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(digest + '\n')
        return True, '%s reinstalled from %s' % (command, checkout)

    def defaults(self) -> PhaseResult:
        """Apply the saved allowlisted macOS preferences (restore semantics, backup first)."""
        snapshot = self.root / '.config/yadm/macos/preferences.plist'
        if self.setup.profile != 'mac' or not snapshot.exists():
            return PhaseResult('skipped', 'macOS preference snapshot not applicable')
        module = load_mac_settings(self.setup.assets / 'mac-settings.py')
        count = module.apply(plistlib.loads(snapshot.read_bytes()), plan=self.setup.args.plan)
        if self.setup.args.plan:
            return PhaseResult('ok', '%d would change' % count)
        return PhaseResult('changed' if count else 'ok', '%d preferences applied' % count)

    def hotkeys(self) -> PhaseResult:
        """Run the hotkeys repo's clash checker and count findings."""
        repo = self.root / 'local/code/web/hotkeys'
        node = self.setup.find('node')
        if self.setup.profile != 'mac' or not (repo / 'scripts/check.js').exists() or not node:
            return PhaseResult('skipped', 'hotkeys checker not available')
        stdout = self.setup.read_ok([node, 'scripts/check.js'], 'check.js failed', cwd=repo)
        counts = count_findings(stdout)
        summary = '%d clashes, %d layer overlaps' % (counts['clash'], counts['layer'])
        return PhaseResult('warn' if counts['clash'] else 'ok', summary, stdout.splitlines()[:20])

    def doctor(self) -> PhaseResult:
        """Doctor checks, including literal home paths in tracked files."""
        failures = self.setup.doctor()
        if not failures:
            return PhaseResult('ok', 'all checks passed')
        homes = [f for f in failures if f.startswith('Absolute home path')]
        summary = '%d items need attention, %d absolute home paths' % (len(failures), len(homes))
        return PhaseResult('warn', summary, failures)
