"""converge sync: converge this machine daily and record per-phase results."""
from __future__ import annotations

import fcntl
import hashlib
import http.client
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
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

STATE_DIR = '.local/state/dotfiles/sync'
PHASES = [('layout', 'Directory layout'),
          ('dotfiles', 'Dotfiles (yadm)'),
          ('keys', 'SSH keys'),
          ('packages', 'Packages'),
          ('repos', 'Repositories (grc)'),
          ('apps', 'Home-made apps'),
          ('declared', 'Declared apps and packages'),  # after packages and apps: report what they could not install
          ('defaults', 'Mac defaults'),
          ('hotkeys', 'Hotkey clash check'),
          ('doctor', 'Doctor'),
          ('recipes', 'Manual steps')]  # last: its checks read every other phase's status
SELF_PRINTING = {'layout', 'doctor'}  # these phases already print their own detail lines
GIT_TIMEOUT, BREW_TIMEOUT, NET_TIMEOUT = 300, 1800, 600  # seconds, for mutating subprocesses
GRC_FALLBACK = 'micromamba/envs/py3/bin/grc'
GLYPHS = {'ok': ('✓', '32'), 'changed': ('✓', '36'), 'skipped': ('-', '2'), 'warn': ('!', '33'), 'failed': ('✗', '31')}  # calm first
DETAIL_LIMIT = 12  # detail lines per group in converge status; --all lifts it
OWN_KEYS = ('id_ed25519.pub', 'id_ecdsa.pub')  # both: MDM-managed Macs accept only ECDSA P-256 keys
STATUS_REFS = 'status/'  # the cluster (off the tailnet) force-pushes its last.json to status/<class>-<host>; the hub's bridge reads it
HUB, HUB_TIMEOUT = 'https://home-gpu.tail2813f4.ts.net/converge', 20  # check-ins and fleet views; CONVERGE_HUB overrides


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


def key_id(line: str) -> str:
    """type and base64 of a public-key line (the comment may differ per copy); '' for blanks and comments."""
    parts = line.split()
    return ' '.join(parts[:2]) if len(parts) >= 2 and parts[1].startswith('AAAA') else ''  # also skips conflict markers


def missing_keys(wanted: List[str], present: List[str]) -> List[str]:
    """Lines of wanted whose key is not already among present."""
    have = {key_id(p) for p in present}
    return [w for w in wanted if key_id(w) and key_id(w) not in have]


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


def skip_list(text: str) -> List[str]:
    """Phase keys from `--skip a,b`; RuntimeError naming the valid keys for an unknown one."""
    keys = [k.strip() for k in text.split(',') if k.strip()]
    unknown = [k for k in keys if k not in dict(PHASES)]
    if unknown:
        raise RuntimeError('--skip: unknown phase %s (phases: %s)' % (', '.join(unknown), ', '.join(k for k, _ in PHASES)))
    return keys


def format_results(phases: Dict[str, PhaseResult]) -> List[str]:
    """Aligned 'key status summary' lines."""
    return ['  %-9s %-8s %s' % (key, r.status, r.summary) for key, r in phases.items()]


def corrective(statuses: Iterable[str]) -> int:
    """How many phases had to change something (Puppet's corrective change): a machine that keeps re-fixing stands out."""
    return sum(1 for status in statuses if status == 'changed')


def write_state(root: Path, phases: Dict[str, PhaseResult], meta: dict) -> Path:
    """Atomically write last.json; a failed write leaves no temp file behind."""
    directory = Path(root) / STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    data = dict(meta, format=1, corrective=corrective(r.status for r in phases.values()),
                phases={k: asdict(v) for k, v in phases.items()})
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
    """Print the last sync: phases with problems last, then each problem's details and every pending recipe's steps
    (how to clear it). Returns its exit code."""
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
    cut = print_problems(problems, root, color, show_all)
    import recipes
    for line in recipes.pending_lines(data.get('pending', [])):
        print(tilde(line, root))
    if cut:
        print('\n  Full lists: converge status --all')
    return int(data['exit'])


def print_problems(problems: List[Tuple[str, PhaseResult]], root: Path, color: bool, show_all: bool) -> bool:
    """Each warn/failed phase with its grouped details (the recipes phase's steps print below instead); whether any were cut."""
    cut = False
    for key, result in problems:
        print('\n  %s  %s' % (paint(key, GLYPHS[result.status][1], color), tilde(result.summary, root)))
        if key == 'recipes' and result.status == 'warn':
            continue
        lines, cut_here = format_details([tilde(d, root) for d in result.details], None if show_all else DETAIL_LIMIT)
        cut |= cut_here
        print('\n'.join(lines))
    return cut


def age(finished: str) -> str:
    """'3h ago' under two days, else '8d ago'."""
    hours = (datetime.now(timezone.utc) - datetime.fromisoformat(finished)).total_seconds() / 3600
    return '%dh ago' % hours if hours < 48 else '%dd ago' % (hours / 24)


def status_ref(machine: str) -> str:
    """Branch that holds a machine's last.json: status/<class>-<host>, ref-safe."""
    return STATUS_REFS + re.sub(r'[^A-Za-z0-9.-]+', '-', machine).strip('-')


def publish_status(setup, yadm: str) -> None:
    """Force-push last.json (and state.json) as a single parentless commit to this machine's status branch."""
    directory = setup.root / STATE_DIR
    machine = json.loads((directory / 'last.json').read_text())['machine']
    entries = ''
    for name in ['last.json', 'state.json']:  # state.json: the effective-state snapshot that fleet --diff compares
        if (directory / name).exists():
            blob = setup.read_ok([yadm, 'hash-object', '-w', directory / name], 'hash-object failed').strip()
            entries += '100644 blob %s\t%s\n' % (blob, name)
    tree = setup.read_ok([yadm, 'mktree'], 'mktree failed', input=entries).strip()
    commit = setup.read_ok([yadm, 'commit-tree', tree, '-m', 'status ' + machine], 'commit-tree failed').strip()
    setup.read_ok([yadm, 'push', '--force', '--quiet', 'origin', '%s:refs/heads/%s' % (commit, status_ref(machine))],
                  'push failed', timeout_s=GIT_TIMEOUT)  # read_ok: GitHub's pull-request hint stays out of the summary


def send_report(setup) -> None:
    """Check this machine in: POST last.json and state.json to the hub, or on the cluster (off the tailnet) push its status branch."""
    if setup.profile == 'cluster':
        yadm = setup.find('yadm')
        if not yadm:
            raise RuntimeError('yadm not on PATH')
        publish_status(setup, yadm)
        return
    directory = setup.root / STATE_DIR
    state = directory / 'state.json'
    report = {'last': json.loads((directory / 'last.json').read_text()),
              'state': json.loads(state.read_text()) if state.exists() else {}}
    request('/report', report)


def hub_url() -> str:
    """Base URL of the hub, without a trailing slash."""
    return os.environ.get('CONVERGE_HUB', HUB).rstrip('/')


def request(path: str, body: Optional[dict] = None) -> bytes:
    """GET a hub path, or POST `body` to it as JSON; RuntimeError naming the URL when the hub does not answer 2xx."""
    url = hub_url() + path
    data = None if body is None else json.dumps(body).encode()
    asked = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(asked, timeout=HUB_TIMEOUT) as answer:
            return answer.read()
    except (OSError, http.client.HTTPException) as exc:  # URLError, HTTPError and timeouts are OSErrors
        raise RuntimeError('%s: %s' % (url, getattr(exc, 'reason', None) or exc))


def fetch(path: str) -> Any:
    """Decoded JSON answer of a hub GET."""
    try:
        return json.loads(request(path))
    except ValueError as exc:
        raise RuntimeError('%s%s: not JSON (%s)' % (hub_url(), path, exc))


def fetch_fleet() -> List[dict]:
    """The hub's newest check-in per host, newest first (see hub.fleet_rows)."""
    return fetch('/fleet')


def fetch_machines() -> List[dict]:
    """Every host's newest snapshot as {machine, profile, state}, the shape snapshot.differences compares."""
    return fetch('/machines')


def stale_lines(rows: List[dict]) -> List[str]:
    """One line per machine the hub marked stale."""
    return ['stale: %s@%s last checked in %s' % (r['class'], r['host'], age(r['finished'])) for r in rows if r['stale']]


def fleet_lines(rows: List[dict]) -> List[str]:
    """The fleet table: host, class, age, exit, phases changed (`fixed`), the phases that were not ok; then the stale machines."""
    lines = []
    for row in rows:
        problems = ' '.join('%s:%s' % (key, status) for key, status in row['phases'].items() if status != 'ok')
        lines.append('%-22s %-8s %-8s exit %-3d fixed %-2d %s' % (
            row['host'], row['class'], age(row['finished']), row['exit'], row['corrective'], problems))
    return [line.rstrip() for line in lines] + stale_lines(rows)


def never_lines(rows: List[dict], expected: Path) -> List[str]:
    """A `never` line for each class in fleet.txt that no machine has checked in as."""
    seen = {row['class'] for row in rows}
    classes = [line.split('#')[0].strip() for line in expected.read_text().splitlines()]
    return ['%-22s %-8s never' % ('?', cls) for cls in classes if cls and cls not in seen]


def difference_lines(states: List[dict], rules: Dict[str, List[str]]) -> List[str]:
    """A count line, then the table of compared snapshot keys that differ between machines (snapshot.EVERY_KEY: every key)."""
    import snapshot
    rows = snapshot.differences(states, rules)
    hosts = [d['machine'].split('@', 1)[1] for d in states if d.get('state')]
    compared = sum(1 for d in states for key in d.get('state') or {} if snapshot.selected(key, rules))
    source = 'everything' if rules == snapshot.EVERY_KEY else 'setup/compare.yml'
    return ['%d differences in %d compared keys (%s)' % (len(rows), compared, source)] + snapshot.table(rows, hosts)


def print_keys(setup) -> int:
    """List this machine's own snapshot from the last sync, to pick compare.yml globs from."""
    path = setup.root / STATE_DIR / 'state.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    for key, value in sorted(state.items()):
        setup.say('%-40s %s' % (key, value if not isinstance(value, list) else ', '.join(map(str, value))))
    setup.say('%d keys (from the last sync; select them in setup/compare.yml)' % len(state))
    return 0


def fleet(setup, expected: Path) -> int:
    """The hub's fleet table plus never-seen classes from fleet.txt: 0 when all clean, 1 otherwise, 2 when the hub is unreachable.
    --checkin sends this machine's last sync first, --diff adds the differing snapshot keys, --keys lists this machine's own."""
    args = setup.args
    if args.keys:
        return print_keys(setup)
    try:
        if args.checkin and args.plan:
            setup.say('plan: check-in not sent')
        elif args.checkin:
            send_report(setup)
        rows = fetch_fleet()
        states = fetch_machines() if args.diff else []
    except RuntimeError as exc:
        print('converge fleet: %s' % exc, file=sys.stderr)
        return 2
    never = never_lines(rows, expected)
    for line in fleet_lines(rows) + never:
        setup.say(line)
    if args.diff:
        import snapshot
        rules = snapshot.EVERY_KEY if args.all else snapshot.load_compare(setup.assets / 'compare.yml')
        setup.say('\n' + '\n'.join(difference_lines(states, rules)))
    unclean = any(r['exit'] or r['stale'] for r in rows)
    return int(unclean or bool(never))


class Sync:
    """Runs the sync phases in order against a Setup instance."""

    def __init__(self, setup, applications: Path = Path('/Applications')):
        self.setup = setup
        self.root = setup.root
        self.applications = Path(applications)
        self.results: Dict[str, PhaseResult] = {}
        self.state: Optional[dict] = None  # this run's snapshot, taken by the recipes phase and reused by _save
        self.pending: List[Any] = []  # recipes.Pending from the recipes phase

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

    def _run_phases(self, skipped: List[str]) -> int:
        """Run all phases except the skipped ones, print the summary; returns 1 if any phase failed."""
        for key, title in PHASES:
            action = (lambda: PhaseResult('skipped', '--skip')) if key in skipped else getattr(self, key)
            self.step(key, title, action)
        self.setup.say('\nSummary')
        for line in format_results(self.results):
            self.setup.say(line)
        return int(any(r.status == 'failed' for r in self.results.values()))

    def _save(self, started: datetime, code: int) -> None:
        """Record this run in last.json and this computer's effective state in state.json."""
        meta = {'started': started.isoformat(), 'finished': datetime.now(timezone.utc).isoformat(),
                'machine': self.machine_label(), 'profile': self.setup.profile, 'exit': code,
                'pending': [asdict(p) for p in self.pending]}
        write_state(self.root, self.results, meta)
        import snapshot
        state = self.state if self.state is not None else snapshot.collect(self.setup, self.applications)
        (self.root / STATE_DIR / 'state.json').write_text(json.dumps(state, indent=1, sort_keys=True))

    def execute(self) -> int:
        """Run every phase; returns 1 if any failed or another sync holds the lock."""
        plan = self.setup.args.plan
        skipped = skip_list(self.setup.args.skip)
        started = datetime.now(timezone.utc)
        label = '%s/%s' % (self.setup.profile, self.setup.machine_class())
        self.setup.say(('SYNC PLAN' if plan else 'DOTFILES SYNC') + ' — ' + label)
        lock = None if plan else acquire_lock(self.root / STATE_DIR / 'lock')
        if not plan and lock is None:
            self.setup.say('another sync is running')
            return 1
        code = 1  # stays 1 if interrupted
        try:
            code = self._run_phases(skipped)
        finally:
            if not plan:
                self._save(started, code)
            if lock is not None:
                lock.close()
        if not plan:
            self.checkin()
        return code

    def checkin(self) -> None:
        """Send this run to the hub and note machines that have gone quiet or differ; never changes the exit code."""
        try:
            send_report(self.setup)
            if self.setup.profile != 'cluster':  # the cluster cannot reach the hub; its status branch is the whole check-in
                self._fleet_notes()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:  # ValueError: unreadable last.json
            self.setup.say('  check-in skipped: %s' % exc)

    def _fleet_notes(self) -> None:
        """Summary lines from the hub's answer: stale machines, and how many compared keys differ."""
        for line in stale_lines(fetch_fleet()):
            self.setup.say('  ' + line)
        import snapshot
        rows = snapshot.differences(fetch_machines(), snapshot.load_compare(self.setup.assets / 'compare.yml'))
        if rows:
            self.setup.say('  differs from the other machines in %d compared keys: converge fleet --diff' % len(rows))

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

    def keys(self) -> PhaseResult:
        """Append every public key in setup/ssh-keys.txt to ~/.ssh/authorized_keys, and this computer's own
        public keys to that tracked list (the next dotfiles phase commits and pushes it)."""
        listed = self.setup.assets / 'ssh-keys.txt'
        authorized = self.root / '.ssh/authorized_keys'
        own = [p for p in (self.root / '.ssh' / n for n in OWN_KEYS) if p.exists()]
        wanted = listed.read_text().splitlines() if listed.exists() else []
        present = authorized.read_text().splitlines() if authorized.exists() else []
        publish = missing_keys([p.read_text().strip() for p in own], wanted)
        add = missing_keys(wanted + publish, present)
        details = ['authorize:' + k.split()[-1] for k in add] + ['publish:' + k.split()[-1] for k in publish]
        if len(own) < len(OWN_KEYS):
            details.append('missing %s: ssh-keygen -t ed25519 and -t ecdsa -b 256 (managed Macs accept only ECDSA)'
                           % ', '.join(n for n in OWN_KEYS if not (self.root / '.ssh' / n).exists()))
        if not (add or publish):
            return PhaseResult('ok', '%d keys authorized' % len([p for p in present if key_id(p)]), details)
        if not self.setup.args.plan:
            if add:
                authorized.parent.mkdir(mode=0o700, exist_ok=True)
                authorized.parent.chmod(0o700)
                authorized.write_text(''.join(line + '\n' for line in present + add))
                authorized.chmod(0o600)
            if publish:
                listed.write_text(''.join(line + '\n' for line in wanted + publish))
        return PhaseResult('changed', '%d keys authorized, %d published' % (len(add), len(publish)), details)

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
        else:  # plan mode inspects only (no --apply); grc's output is kept so a check-in says what went wrong
            apply = [] if self.setup.args.plan else ['--apply']
            done = self.setup.read([grc, 'active', 'sync', *apply, '--config', config], timeout_s=NET_TIMEOUT)
            output = (done.stdout + done.stderr).strip().splitlines()
            details += output[-30:]
            if done.returncode:  # a broken repo sync must not stop `s` from being refreshed below
                words = [line for line in output if re.search(r'[A-Za-z]', line)]  # skip table borders
                last = (words or ['no output'])[-1].strip('│ ')[:120]
                status, summary = 'failed', 'grc active sync failed: exit %d: %s' % (done.returncode, last)
            else:
                status, summary = 'ok', 'grc active sync ' + ' '.join(apply or ['(inspect)'])
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

    def declared(self) -> PhaseResult:
        """GUI apps, launch agents, login items and Linux packages against setup/declared/ (declared.py)."""
        import declared
        return declared.declared(self.setup, self.setup.machine_class(), self.setup.profile)

    def defaults(self) -> PhaseResult:
        """Apply the saved allowlisted macOS preferences (restore semantics, backup first)."""
        snapshot = self.root / '.config/yadm/macos/preferences.plist'
        if self.setup.profile != 'mac' or not snapshot.exists() or self.setup.lean():
            return PhaseResult('skipped', 'macOS preference snapshot not applicable')
        module = load_mac_settings(self.setup.assets / 'mac-settings.py')
        count = module.apply(plistlib.loads(snapshot.read_bytes()), plan=self.setup.args.plan)
        if self.setup.args.plan:
            return PhaseResult('ok', '%d would change' % count)
        return PhaseResult('changed' if count else 'ok', '%d preferences applied' % count)

    def hotkeys(self) -> PhaseResult:
        """Run the hotkeys repo's clash checker and check that Karabiner is actually applying karabiner.json.
        On Linux, converge Toshy + GNOME to ~/.config/hotkeys/linux instead (sync_linux)."""
        if self.setup.profile == 'linux':
            import sync_linux
            return PhaseResult(*sync_linux.hotkeys(self.setup))
        repo = self.root / 'local/code/web/hotkeys'
        node = self.setup.find('node')
        if self.setup.profile != 'mac' or not (repo / 'scripts/check.js').exists() or not node:
            return PhaseResult('skipped', 'hotkeys checker not available')
        stdout = self.setup.read_ok([node, 'scripts/check.js'], 'check.js failed', cwd=repo)
        counts = count_findings(stdout)
        import sync_mac
        problems, notes = sync_mac.karabiner_health(self.setup)  # a tracked karabiner.json is useless unless Karabiner applies it
        summary = '%d clashes, %d layer overlaps' % (counts['clash'], counts['layer'])
        if problems:
            summary += ', %d Karabiner problems' % len(problems)
        details = problems + notes + stdout.splitlines()[:20]
        return PhaseResult('warn' if counts['clash'] or problems else 'ok', summary, details)

    def doctor(self) -> PhaseResult:
        """Doctor checks, including literal home paths in tracked files."""
        failures = self.setup.doctor()
        if not failures:
            return PhaseResult('ok', 'all checks passed')
        homes = [f for f in failures if f.startswith('Absolute home path')]
        summary = '%d items need attention, %d absolute home paths' % (len(failures), len(homes))
        return PhaseResult('warn', summary, failures)

    def recipes(self) -> PhaseResult:
        """Snapshot this machine, then list the recipes whose checks fail (recipes.py); _save writes the snapshot and `pending`."""
        import recipes
        import snapshot
        self.state = snapshot.collect(self.setup, self.applications)
        result, self.pending = recipes.phase(self.setup, self.state, {k: r.status for k, r in self.results.items()})
        return result
