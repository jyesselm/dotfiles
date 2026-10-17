"""dotfiles-setup --sync: converge this machine daily and record per-phase results."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import platform
import plistlib
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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


def status_lines(root: Path, schedule_installed: bool) -> Tuple[List[str], int]:
    """Lines describing the last sync, and its stored exit code (1 if none yet)."""
    path = Path(root) / STATE_DIR / 'last.json'
    if not path.exists():
        return ['No sync has run yet; try dotfiles-setup --sync --plan'], 1
    data = json.loads(path.read_text())
    finished = datetime.fromisoformat(data['finished'])
    hours = (datetime.now(timezone.utc) - finished).total_seconds() / 3600
    lines = ['Last sync: %s (%.0fh ago) on %s, exit %d' % (data['finished'], hours, data['machine'], data['exit'])]
    lines += format_results({k: PhaseResult(**v) for k, v in data['phases'].items()})
    lines.append('Schedule: ' + ('installed' if schedule_installed else 'not installed'))
    return lines, int(data['exit'])


def print_status(root: Path, schedule_installed: bool) -> int:
    """Print the last sync result; returns its stored exit code (1 if none yet)."""
    lines, code = status_lines(root, schedule_installed)
    print('\n'.join(lines))
    return code


def read_fleet(path: Path) -> List[Tuple[str, str]]:
    """(ssh host, class) pairs from fleet.txt; blank lines and # comments are ignored."""
    hosts = []
    for line in Path(path).read_text().splitlines():
        words = line.split('#')[0].split()
        if words:
            hosts.append((words[0], words[1] if len(words) > 1 else '?'))
    return hosts


def summarize_status(output: str, code: int) -> Tuple[str, str, str]:
    """(age, exit, phases not ok) from --status output; ssh/transport failures read as unreachable."""
    if code in (124, 255):
        return 'unreachable', '-', ''
    head = re.match(r'Last sync: \S+ \((\d+)h ago\) on \S+, exit (\d+)', output)
    if not head:
        if 'No sync has run yet' in output:
            return 'never', str(code), ''
        return 'no status', str(code), (output.strip().splitlines() or [''])[0][:40]
    phases = re.findall(r'^  (\w+)\s+(\w+)\s', output, re.M)
    return head.group(1) + 'h ago', head.group(2), ' '.join('%s:%s' % p for p in phases if p[1] != 'ok')


def fleet(setup, schedule_installed: bool, path: Path, connect_timeout: int = 10) -> int:
    """One line per machine (this one first, then fleet.txt over ssh); 1 unless every machine synced cleanly."""
    local_host = platform.node().split('.')[0]
    lines, code = status_lines(setup.root, schedule_installed)
    rows = [(local_host, setup.machine_class(), summarize_status('\n'.join(lines), code))]
    for host, cls in read_fleet(path):
        done = setup.read(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % connect_timeout, host,
                           '~/.local/bin/dotfiles-setup --status'], timeout_s=connect_timeout + 60)
        rows.append((host, cls, summarize_status(done.stdout, done.returncode)))
    for host, cls, (age, exit_code, phases) in rows:
        setup.say('%-14s %-8s %-12s exit %-3s %s' % (host, cls, age, exit_code, phases))
    return int(any(exit_code != '0' for _, _, (_, exit_code, _) in rows))


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
        return code

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
        summary = 'created %d, missing-check %d, unplanned %d' % (
            len(report.created), len(report.expected), len(report.unplanned))
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
        details += ['live settings differ from tracked; reconcile then run dotfiles-setup: ' + p for p in held]
        if not online:
            summary = 'remote unreachable (%s): committed %d files locally; pull/push skipped' % (why, len(files))
            return PhaseResult('warn', summary, details)
        if deleted:
            return PhaseResult('warn', self._paused_summary(deleted), details)
        status = 'changed' if (files or pulled or pushed) else 'ok'
        if held:
            status = 'warn'
        return PhaseResult(status, 'committed %d, pulled %s, pushed %s' % (len(files), pulled, pushed), details)

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
        """Clone and fast-forward the repos listed for git-repo-checker."""
        grc = self.setup.find('grc')
        fallback = self.root / GRC_FALLBACK
        grc = grc or (str(fallback) if fallback.exists() else None)
        config = self.root / '.config/git-repo-checker/active.yml'
        if not grc or not config.exists():
            return PhaseResult('skipped', 'grc or active.yml missing; repos not synced')
        self.setup.run([grc, 'active', 'sync', '--apply', '--quiet', '--config', config], timeout=NET_TIMEOUT)
        return PhaseResult('ok', 'grc active sync --apply')

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
