"""Effective-state snapshot of this computer, pushed with each check-in so `converge fleet --diff` can compare machines.

Git already makes the tracked files identical everywhere; what differs between machines is untracked state (installed
versions, loaded configs, keyboards, shortcut flags, login items). Every gatherer is cheap and read-only; one that fails
records `error: ...` under its key instead of losing the whole snapshot. setup/compare.yml selects which keys are compared.
"""
from __future__ import annotations

import fnmatch
import json
import platform
import plistlib
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Tuple

Value = object  # str or list of str
GLOBAL_KEYS = ['AppleInterfaceStyle', 'KeyRepeat', 'InitialKeyRepeat', 'com.apple.keyboard.fnState',
               'AppleShowAllExtensions', 'ApplePressAndHoldEnabled', 'NSAutomaticSpellingCorrectionEnabled']
SHORTCUTS = {28: 'screenshot-file', 29: 'screenshot-clipboard', 30: 'area-file', 31: 'area-clipboard', 32: 'mission-control',
             33: 'app-windows', 36: 'show-desktop', 60: 'input-source', 61: 'input-source-next', 64: 'spotlight', 65: 'finder-search',
             79: 'space-left', 81: 'space-right', 118: 'space-1', 119: 'space-2', 120: 'space-3', 121: 'space-4',
             160: 'launchpad', 162: 'notification-center', 163: 'do-not-disturb', 175: 'accessibility', 184: 'screenshot-options'}
APP_DIRS = ['/Applications', '~/Applications']


def _version(text: str) -> str:
    found = re.search(r'\d+\.\d+(?:\.\d+)*', text)
    return found.group(0) if found else text.strip().splitlines()[0][:40] if text.strip() else 'unknown'


def _git_head(setup, checkout: Path) -> str:
    """Short HEAD, with +dirty when the working tree has uncommitted changes (the usual 'newer version on my desktop')."""
    head = setup.read(['git', '-C', str(checkout), 'rev-parse', '--short', 'HEAD'])
    if head.returncode:
        return 'not a repo'
    dirty = setup.read(['git', '-C', str(checkout), 'status', '--porcelain']).stdout.strip()
    return head.stdout.strip() + ('+dirty' if dirty else '')


def active_repos(path: Path) -> List[str]:
    """Checkout paths from git-repo-checker's active.yml (`- path: ...` lines; no yaml module needed)."""
    if not path.exists():
        return []
    return [m.group(1).strip().strip('\'"') for m in re.finditer(r'^- path:\s*(.+)$', path.read_text(), re.M)]


def _module(setup):
    """The setup module (TOOLS, CHECKOUT_TOOLS), however it was loaded (as __main__, imported, or from a file in tests)."""
    module = sys.modules.get(type(setup).__module__)
    if module is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location('setup_constants', setup.assets / 'setup.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def common(setup) -> Dict[str, Callable[[], Value]]:
    """Gatherers for every profile."""
    root, module = setup.root, _module(setup)
    def dotfiles() -> Dict[str, str]:
        yadm = setup.find('yadm')
        if not yadm:
            return {'head': 'yadm missing'}
        head = setup.read([yadm, 'rev-parse', '--short', 'HEAD']).stdout.strip() or 'unknown'
        dirty = setup.read([yadm, 'status', '--porcelain']).stdout.strip()
        return {'head': head, 'dirty': str(len(dirty.splitlines())) + ' files' if dirty else 'clean'}

    gatherers: Dict[str, Callable[[], Value]] = {
        'dotfiles': dotfiles,  # the tracked layer itself: every machine should sit at the same commit, clean
        'os': lambda: '%s %s %s' % (platform.system(), platform.mac_ver()[0] or platform.release(), platform.machine()),
        'git.email': lambda: setup.read(['git', 'config', 'user.email']).stdout.strip() or 'unset',
        'ssh.keys': lambda: sorted(p.name for p in (root / '.ssh').glob('*.pub')),
        'gh.auth': lambda: ('ok' if setup.read([setup.find('gh'), 'auth', 'status']).returncode == 0 else 'not logged in')
        if setup.find('gh') else 'gh missing',
    }
    for name in module.TOOLS:
        gatherers['tools.' + name] = (lambda n=name: _version(setup.read([setup.find(n), '-V' if n == 'tmux' else '--version']).stdout)
                                      if setup.find(n) else 'missing')

    def uv_tools() -> Dict[str, str]:
        if not setup.find('uv'):
            return {}
        out = setup.read([setup.find('uv'), 'tool', 'list']).stdout
        return {m.group(1): m.group(2) for m in re.finditer(r'^(\S+) v(\S+)', out, re.M)}
    gatherers['uv'] = uv_tools  # a dict gatherer spreads into uv.<tool> keys

    def checkouts() -> Dict[str, str]:
        paths = {setup.checkout(c) for c in module.CHECKOUT_TOOLS}
        paths |= {root / p for p in active_repos(root / '.config/git-repo-checker/active.yml')}
        return {p.name: _git_head(setup, p) for p in sorted(paths) if (p / '.git').exists()}
    gatherers['checkouts'] = checkouts
    return gatherers


def shortcut_flags(plist: bytes) -> Dict[str, str]:
    """`defaults export com.apple.symbolichotkeys` -> {'shortcuts.31 area-clipboard': 'on 52 21 1441792'}: every id, named when known."""
    data = plistlib.loads(plist).get('AppleSymbolicHotKeys', {}) if plist else {}
    flags = {}
    for key, entry in data.items():
        label = '%s %s' % (key, SHORTCUTS[int(key)]) if str(key).isdigit() and int(key) in SHORTCUTS else str(key)
        params = ' '.join(str(p) for p in entry.get('value', {}).get('parameters', []))
        flags['shortcuts.' + label] = ('on ' + params).strip() if entry.get('enabled') else 'off'
    return flags


def app_versions(dirs: List[Path]) -> Dict[str, str]:
    """{'apps.Name': version} for every top-level .app bundle."""
    apps = {}
    for base in dirs:
        for bundle in sorted(base.glob('[!.]*.app')) if base.is_dir() else []:  # hidden bundles are helpers, not apps
            try:
                info = plistlib.loads((bundle / 'Contents/Info.plist').read_bytes())
                apps['apps.' + bundle.stem] = str(info.get('CFBundleShortVersionString') or info.get('CFBundleVersion') or '?')
            except Exception:  # noqa: BLE001 - unreadable or malformed Info.plist (expat errors are not ValueErrors)
                apps['apps.' + bundle.stem] = '?'
    return apps


def mac(setup, applications: Path) -> Dict[str, Callable[[], Value]]:
    """Gatherers that only make sense on a Mac."""
    import sync_mac
    root = setup.root

    def brew() -> Dict[str, str]:
        tool = setup.find('brew')
        if not tool:
            return {}
        chosen = set(setup.read([tool, 'leaves', '--installed-on-request']).stdout.split())  # not their dependencies
        lines = setup.read([tool, 'list', '--versions']).stdout + setup.read([tool, 'list', '--cask', '--versions']).stdout
        casks = set(setup.read([tool, 'list', '--cask', '-1']).stdout.split())
        return {line.split()[0]: ' '.join(line.split()[1:]) for line in lines.splitlines()
                if line.split() and line.split()[0] in chosen | casks}

    def defaults_live() -> Dict[str, str]:
        from sync import load_mac_settings
        module = load_mac_settings(setup.assets / 'mac-settings.py')
        values = {}
        for domain, record in module.capture()['domains'].items():
            values.update({'%s.%s' % (domain, k): json.dumps(v, default=str) for k, v in record['values'].items()})
            values.update({'%s.%s' % (domain, k): 'unset' for k in record['unset']})
        return values

    def karabiner() -> Dict[str, str]:
        info = Path(sync_mac.KARABINER['app']) / 'Contents/Info.plist'
        config = root / sync_mac.KARABINER['config']
        if not info.exists():
            return {'installed': 'no'}
        problems, notes = sync_mac.karabiner_health(setup)
        state = {'version': str(plistlib.loads(info.read_bytes()).get('CFBundleShortVersionString')),
                 'config': config.exists() and json.loads(config.read_text()).get('profiles', [{}])[0].get('name', '?') or 'absent',
                 'keyboards': sum([n.split(': ', 1)[1].split(', ') for n in notes if n.startswith('Karabiner grabs: ')], []) or ['none'],
                 'problems': problems or 'none'}
        return state

    def login_items() -> Value:
        done = setup.read(['osascript', '-e', 'tell application "System Events" to get the name of every login item'])
        return sorted(x.strip() for x in done.stdout.split(',') if x.strip()) if done.returncode == 0 else 'unavailable'

    return {
        'brew': brew,
        'apps': lambda: {k[len('apps.'):]: v for k, v in app_versions([applications] + [root / 'Applications']).items()},
        'defaults': defaults_live,
        'shortcuts': lambda: {k[len('shortcuts.'):]: v for k, v in
                              shortcut_flags(setup.read(['defaults', 'export', 'com.apple.symbolichotkeys', '-']).stdout.encode()).items()},
        'keys.fnState': lambda: setup.read(['defaults', 'read', '-g', 'com.apple.keyboard.fnState']).stdout.strip() or 'unset',
        'karabiner': karabiner,
        'launchagents': lambda: sorted(p.name for p in (root / 'Library/LaunchAgents').glob('*.plist')),
        'fonts': lambda: sorted(p.name for p in (root / 'Library/Fonts').iterdir()) if (root / 'Library/Fonts').is_dir() else [],
        'login_items': login_items,
    }


def collect(setup, applications: Path = Path('/Applications')) -> Dict[str, Value]:
    """Flat {key: value} of this computer's effective state; dict-valued gatherers spread into dotted keys."""
    state: Dict[str, Value] = {}
    try:
        gatherers = common(setup)
        if setup.profile == 'mac':
            gatherers.update(mac(setup, applications))
    except Exception as exc:  # noqa: BLE001 - a snapshot problem must never fail the sync that just ran
        return {'error': str(exc).splitlines()[0][:100]}
    for key, gather in gatherers.items():
        try:
            value = gather()
        except Exception as exc:  # noqa: BLE001 - one broken gatherer must not lose the snapshot
            value = 'error: %s' % str(exc).splitlines()[0][:100]
        if isinstance(value, dict):
            state.update({'%s.%s' % (key, k): v for k, v in value.items()})
        else:
            state[key] = value
    return state


def load_compare(path: Path) -> Dict[str, List[str]]:
    """Read compare.yml: a mapping of lists (`compare:` / `ignore:` with `- glob` items). Only that subset of YAML is used."""
    lists: Dict[str, List[str]] = {'compare': [], 'ignore': []}
    current = None
    for raw in path.read_text().splitlines() if path.exists() else []:
        line = raw.split('#', 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((' ', '-')) and line.endswith(':'):
            current = line[:-1].strip()
            lists.setdefault(current, [])
        elif line.strip().startswith('- ') and current:
            lists[current].append(line.strip()[2:].strip().strip('\'"'))
        else:
            raise ValueError('%s: cannot read line %r (expected `section:` or `- pattern`)' % (path.name, raw))
    return lists


def selected(key: str, rules: Dict[str, List[str]]) -> bool:
    return any(fnmatch.fnmatch(key, p) for p in rules['compare']) and not any(fnmatch.fnmatch(key, p) for p in rules['ignore'])


def differences(statuses: List[dict], rules: Dict[str, List[str]], everything: bool = False) -> List[Tuple[str, Dict[str, Value]]]:
    """(key, {host: value}) for each selected key whose value differs among machines of the same profile that have that group."""
    machines = [(d['machine'].split('@', 1)[1], d.get('profile', '?'), d.get('state') or {}) for d in statuses]
    rows = []
    for key in sorted({k for _, _, state in machines for k in state}):
        if not everything and not selected(key, rules):
            continue
        group = key.split('.')[0]
        profiles = {profile for _, profile, state in machines if key in state}
        values = {host: state.get(key, '-') for host, profile, state in machines
                  if profile in profiles and any(k == group or k.startswith(group + '.') for k in state)}  # no apps at all: not compared on apps
        if len({json.dumps(v, sort_keys=True) for v in values.values()}) > 1:
            rows.append((key, values))
    return rows


def show(value: Value, others: List[Value] = (), width: int = 50) -> str:
    """A cell: a list shows only what this machine lacks compared with the others (`lacks: a, b`), so long lists stay readable."""
    if isinstance(value, list):
        union = [x for other in others if isinstance(other, list) for x in other]
        lacking = sorted({str(x) for x in union if x not in value})
        text = 'lacks: ' + ', '.join(lacking) if lacking else 'has all'
    else:
        text = str(value)
    return text if len(text) <= width else text[:width - 1] + '…'


def table(rows: List[Tuple[str, Dict[str, Value]]], hosts: List[str]) -> List[str]:
    """Aligned lines: a header of hosts, then one line per differing key."""
    if not rows:
        return []
    cells = [(key, [show(values.get(h, ''), [v for o, v in values.items() if o != h]) for h in hosts]) for key, values in rows]
    key_width = max(len('key'), *(len(k) for k, _ in cells))
    widths = [max(len(h), *(len(c[i]) for _, c in cells)) for i, h in enumerate(hosts)]
    fmt = lambda key, row: '  '.join([key.ljust(key_width)] + [c.ljust(w) for c, w in zip(row, widths)]).rstrip()
    return [fmt('key', hosts)] + [fmt(key, row) for key, row in cells]
