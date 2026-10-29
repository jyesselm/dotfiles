"""Declared vs present: GUI apps, launch agents, login items and Linux packages (setup/declared/*.txt).

Each kind has a declaration file, an observer (what this machine has) and, where a program can do it without sudo,
an installer. The `declared` sync phase reports what is wanted here but missing and what is present but undeclared;
removal is never automatic. Missing entries no program can install become recipes (`pending`), so the hub and
`converge status` show one list of manual steps.
"""
from __future__ import annotations

import fnmatch
import plistlib
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import layout as lay
from recipes import Pending
from sync import NET_TIMEOUT, PhaseResult

DECLARED_DIR = 'declared'  # under setup/
APP_DIRS = ('/Applications', '~/Applications')
SYSTEM_APPS = '/System/Applications'  # Apple's own: observed so a declared one counts as present, never reported as undeclared
APPLE_APPS = ('Safari', 'Keynote', 'Pages', 'Numbers', 'GarageBand', 'iMovie', 'Xcode')  # Apple's apps that live in /Applications
VENDOR_AGENTS = ('homebrew.mxcl.*', 'sh.brew.*', 'com.google.keystone.*', 'com.google.GoogleUpdater.*',  # updaters, brew services
                 'com.dropbox.DropboxUpdater.*', 'com.dropbox.dropboxmacupdate.*', 'com.grammarly.ProjectLlama.*',
                 'com.valvesoftware.steamclean')
SOURCES = ('brew', 'release', 'mas', 'manual', 'system')  # how an app gets onto a Mac (apps.txt source:)
MANUAL_SOURCES = ('', 'mas', 'manual')  # missing entries a person installs: they become recipes ('' = kinds without source:)
FLAGS = ('allowed',)
VALID = {'class': lambda v: set(v.split(',')) <= lay.CLASSES, 'source': lambda v: v in SOURCES,
         'url': lambda v: v.startswith('https://'), 'cask': bool}


@dataclass
class Entry:
    """One declaration line: `name  key:value ...  [allowed]`."""
    name: str
    allowed: bool = False
    qualifiers: Dict[str, str] = field(default_factory=dict)

    @property
    def classes(self) -> Optional[Set[str]]:
        """Classes this entry is wanted on; None means every class of the kind's profile."""
        value = self.qualifiers.get('class')
        return set(value.split(',')) if value else None

    @property
    def source(self) -> str:
        """How the app gets installed (apps.txt); '' for kinds without source:."""
        return self.qualifiers.get('source', '')


@dataclass(frozen=True)
class Kind:
    """One kind of declared thing: its profile, observer, optional installer, built-in ignore and hint builder."""
    name: str
    profiles: Tuple[str, ...]
    observe: Callable[[Any], List[str]]
    hint: Callable[[List[Entry]], List[Tuple[str, str]]]  # (subject, action) per missing entry, or one for the batch
    install: Optional[Callable[[Any, List[str]], None]] = None
    ignore: Callable[[Any], Sequence[str]] = lambda setup: ()  # globs never reported as undeclared
    keys: Tuple[str, ...] = ('class',)  # qualifiers the file may use; a kind that takes source: requires it
    manual: bool = True  # missing entries become recipes (agents come from an app or a tracked plist instead)

    @property
    def file(self) -> str:
        """The declaration file under setup/declared/."""
        return self.name + '.txt'


@dataclass
class Outcome:
    """What one kind found on this machine."""
    kind: Kind
    missing: List[Entry] = field(default_factory=list)
    undeclared: List[str] = field(default_factory=list)
    error: str = ''

    def details(self) -> List[str]:
        """Phase detail lines: grouped missing:/undeclared: names, then how to fix each missing one."""
        if self.error:
            return ['%s: %s' % (self.kind.name, self.error)]
        lines = ['missing:%s (%s)' % (e.name, self.kind.name) for e in self.missing]
        lines += ['undeclared:%s (%s)' % (n, self.kind.name) for n in self.undeclared]
        return lines + ['%s: %s' % pair for pair in self.kind.hint(self.missing)]


# --- parsing and comparison ---------------------------------------------------------------------------------------

def parse(text: str, keys: Sequence[str] = tuple(VALID)) -> List[Entry]:
    """Entries of a declaration file; ValueError naming the line for an unknown or malformed qualifier."""
    return [_entry(number, line, keys) for number, line in lay.manifest_lines(text)]


def _entry(number: int, line: str, keys: Sequence[str]) -> Entry:
    """One parsed line: the entry name may contain spaces, the qualifiers are the trailing key:value / allowed tokens."""
    name, tokens = lay.split_qualifiers(line, FLAGS)
    entry = Entry(name, allowed='allowed' in tokens)
    for token in [t for t in tokens if t not in FLAGS]:
        key, _, value = token.partition(':')
        if key not in keys or not VALID[key](value):
            raise ValueError('line %d: bad qualifier %r (allowed here: %s, allowed)' % (number, token, ', '.join(keys)))
        entry.qualifiers[key] = value
    if 'source' in keys and not entry.source:
        raise ValueError('line %d: %s needs source:%s' % (number, name, '|'.join(SOURCES)))
    return entry


def compare(entries: List[Entry], present: List[str], machine_class: str) -> Tuple[List[str], List[str]]:
    """(missing, undeclared) names: wanted here but absent, and present but neither wanted here nor allowed."""
    wanted = {e.name for e in entries if not e.allowed and (e.classes is None or machine_class in e.classes)}
    allowed = {e.name for e in entries if e.allowed}
    have = set(present)
    return sorted(wanted - have), sorted(have - wanted - allowed)


def load(setup, kind: Kind) -> List[Entry]:
    """The kind's declaration file (an absent file declares nothing); ValueError names the file."""
    path = setup.assets / DECLARED_DIR / kind.file
    if not path.exists():
        return []
    try:
        return parse(path.read_text(), kind.keys)
    except ValueError as exc:
        raise ValueError('%s/%s %s' % (DECLARED_DIR, kind.file, exc))


def check(setup, kind: Kind, machine_class: str) -> Outcome:
    """Observe one kind and compare it with its declarations; an observer failure is recorded, not raised."""
    entries = load(setup, kind)
    try:
        present = kind.observe(setup)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return Outcome(kind, error='could not list: %s' % exc)
    missing, undeclared = compare(entries, present, machine_class)
    ignore = kind.ignore(setup)
    wanted = {e.name: e for e in entries if not e.allowed}
    return Outcome(kind, [wanted[name] for name in missing], [n for n in undeclared if not _ignored(n, ignore)])


def _ignored(name: str, globs: Sequence[str]) -> bool:
    """Whether a built-in ignore glob matches the name."""
    return any(fnmatch.fnmatchcase(name, glob) for glob in globs)


# --- observers ------------------------------------------------------------------------------------------------------

def _home(setup, directory: str) -> Path:
    """A `~/`-relative directory resolved against this setup's home."""
    return setup.root / directory[2:] if directory.startswith('~/') else Path(directory)


def bundle_names(directory: Path) -> List[str]:
    """Names (without .app) of the visible top-level bundles in a directory."""
    return sorted(p.stem for p in directory.glob('[!.]*.app')) if directory.is_dir() else []


def observe_apps(setup) -> List[str]:
    """Every app in /Applications, ~/Applications and /System/Applications."""
    names: Set[str] = set()
    for directory in APP_DIRS + (SYSTEM_APPS,):
        names.update(bundle_names(_home(setup, directory)))
    return sorted(names)


def apple_apps(setup) -> List[str]:
    """Apple's own apps, never reported as undeclared: APPLE_APPS plus everything in /System/Applications."""
    return list(APPLE_APPS) + bundle_names(_home(setup, SYSTEM_APPS))


def agent_label(path: Path) -> str:
    """The Label of a LaunchAgent plist; its file name when the plist is unreadable."""
    try:
        return str(plistlib.loads(path.read_bytes()).get('Label') or path.stem)
    except Exception:  # noqa: BLE001 - malformed plists raise expat errors, not ValueErrors
        return path.stem


def observe_agents(setup) -> List[str]:
    """Labels of the user's LaunchAgents."""
    return sorted({agent_label(p) for p in (setup.root / 'Library/LaunchAgents').glob('*.plist')})


def observe_login_items(setup) -> List[str]:
    """Login items from the snapshot's System Events gatherer; RuntimeError when it does not answer."""
    import snapshot
    items = snapshot.login_items(setup)
    if not isinstance(items, list):
        raise RuntimeError('System Events did not answer (%s)' % items)
    return items


def _output(setup, argv: List[str]) -> str:
    """stdout of a read-only listing; '' when the tool is not installed here."""
    if not setup.find(argv[0]):
        return ''
    return setup.read_ok(argv, argv[0] + ' failed')


def apt_manual(setup) -> List[str]:
    """Packages installed on request (not as dependencies)."""
    return _output(setup, ['apt-mark', 'showmanual']).split()


def snap_versions(setup) -> Dict[str, str]:
    """{snap: version} from `snap list`."""
    rows = [line.split() for line in _output(setup, ['snap', 'list']).splitlines()[1:]]  # first line is the header
    return {row[0]: row[1] for row in rows if len(row) > 1}


def flatpak_versions(setup) -> Dict[str, str]:
    """{application id: version} of the installed flatpak apps (user and system)."""
    out = _output(setup, ['flatpak', 'list', '--app', '--columns=application,version'])
    rows = [line.split('\t') for line in out.splitlines() if line.strip()]
    return {row[0].strip(): row[1].strip() if len(row) > 1 else '' for row in rows}


def gnome_enabled(setup) -> List[str]:
    """UUIDs of the enabled GNOME Shell extensions (Setup points cron runs at the session bus)."""
    return _output(setup, ['gnome-extensions', 'list', '--enabled']).split()


# --- installers (no sudo) -------------------------------------------------------------------------------------------

def install_flatpaks(setup, ids: List[str]) -> None:
    """Install each missing flatpak for this user from Flathub; a failure leaves it missing (re-observed after)."""
    for app_id in ids:
        try:
            setup.run(['flatpak', 'install', '--user', '-y', 'flathub', app_id], timeout=NET_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            setup.say('  %s not installed: %s' % (app_id, exc))


def enable_extensions(setup, uuids: List[str]) -> None:
    """Enable the missing extensions that are installed but off; the rest stay missing (a recipe installs them)."""
    installed = set(_output(setup, ['gnome-extensions', 'list']).split())
    for uuid in [u for u in uuids if u in installed]:
        try:
            setup.run(['gnome-extensions', 'enable', uuid], timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            setup.say('  %s not enabled: %s' % (uuid, exc))


# --- hints: how a person fixes a missing entry ------------------------------------------------------------------------

def cask_token(entry: Entry) -> str:
    """The cask that installs a source:brew app: its cask: qualifier, else the name lower-cased with dashes."""
    return entry.qualifiers.get('cask') or entry.name.lower().replace(' ', '-')


def app_action(entry: Entry) -> str:
    """How a missing app gets installed, by its source."""
    actions = {'brew': 'brew install --cask %s' % cask_token(entry),
               'release': 'converge sync (the apps phase installs it from setup/apps.json)',
               'mas': 'App Store: search "%s"' % entry.name,
               'manual': 'download: %s' % entry.qualifiers['url'] if 'url' in entry.qualifiers
               else 'install it by hand (add url: to setup/declared/apps.txt)',
               'system': 'System Settings > General > Software Update'}
    return actions[entry.source]


def each(action: Callable[[Entry], str]) -> Callable[[List[Entry]], List[Tuple[str, str]]]:
    """A hint builder with one (name, action) pair per missing entry."""
    return lambda entries: [(e.name, action(e)) for e in entries]


def batch(command: str) -> Callable[[List[Entry]], List[Tuple[str, str]]]:
    """A hint builder with one command line for every missing entry."""
    return lambda entries: [('packages', '%s %s' % (command, ' '.join(e.name for e in entries)))] if entries else []


KINDS: Dict[str, Kind] = {kind.name: kind for kind in [
    Kind('apps', ('mac',), observe_apps, each(app_action), ignore=apple_apps, keys=('class', 'source', 'url', 'cask')),
    Kind('agents', ('mac',), observe_agents,
         each(lambda e: 'reinstall the app or tracked plist that provides ~/Library/LaunchAgents/%s.plist' % e.name),
         ignore=lambda setup: VENDOR_AGENTS, manual=False),
    Kind('login-items', ('mac',), observe_login_items, each(lambda e: 'System Settings > General > Login Items > "+" > %s' % e.name)),
    Kind('apt', ('linux',), apt_manual, batch('sudo apt install')),
    Kind('snap', ('linux',), lambda setup: sorted(snap_versions(setup)), batch('sudo snap install')),
    Kind('flatpak', ('linux',), lambda setup: sorted(flatpak_versions(setup)),
         each(lambda e: 'flatpak install --user -y flathub ' + e.name),
         install=install_flatpaks),
    Kind('gnome-extensions', ('linux',), gnome_enabled, each(lambda e: 'https://extensions.gnome.org (search "%s", Install)' % e.name),
         install=enable_extensions),
]}


# --- the sync phase -------------------------------------------------------------------------------------------------

def kinds_for(profile: str) -> List[Kind]:
    """The kinds declared for machines of this profile, in table order."""
    return [kind for kind in KINDS.values() if profile in kind.profiles]


def settle(setup, kind: Kind, machine_class: str) -> Tuple[Outcome, int]:
    """(outcome after installing what the kind's installer can, how many it fixed); --plan never installs."""
    outcome = check(setup, kind, machine_class)
    if not outcome.missing or kind.install is None or setup.args.plan:
        return outcome, 0
    kind.install(setup, [e.name for e in outcome.missing])
    after = check(setup, kind, machine_class)
    return after, len(outcome.missing) - len(after.missing)


def declared(setup, machine_class: str, profile: str) -> PhaseResult:
    """Compare every kind declared for this profile with what is present: ok, changed (the installers fixed everything),
    or warn with the missing and undeclared names and how to fix each missing one."""
    kinds = kinds_for(profile)
    if not kinds:
        return PhaseResult('skipped', 'nothing is declared for %s machines' % profile)
    settled = [settle(setup, kind, machine_class) for kind in kinds]
    outcomes = [outcome for outcome, _ in settled]
    fixed = sum(count for _, count in settled)
    missing = sum(len(o.missing) for o in outcomes)
    undeclared = sum(len(o.undeclared) for o in outcomes)
    failed = [o.kind.name for o in outcomes if o.error]
    names = ', '.join(kind.name for kind in kinds)
    if not (missing or undeclared or failed):
        return PhaseResult('changed' if fixed else 'ok', ('%d installed; ' % fixed if fixed else '') + 'all declared: ' + names)
    summary = '%d missing, %d undeclared (%s)' % (missing, undeclared, names)
    if failed:
        summary += '; could not list ' + ', '.join(failed)
    installable = sum(len(o.missing) for o in outcomes if o.kind.install)
    if setup.args.plan and installable:
        summary += '; %d would be installed' % installable
    details = [line for outcome in outcomes for line in outcome.details()]
    return PhaseResult('warn', summary, details)


# --- snapshot keys and generated recipes ------------------------------------------------------------------------------

def snapshot(setup) -> Dict[str, object]:
    """{'<kind>.missing': [...], '<kind>.undeclared': [...]} for this profile's kinds (snapshot.py prefixes `declared.`)."""
    values: Dict[str, object] = {}
    for kind in kinds_for(setup.profile):
        try:
            outcome = check(setup, kind, setup.machine_class())
        except ValueError as exc:  # a broken declaration file: the declared phase already failed on it
            outcome = Outcome(kind, error=str(exc))
        if outcome.error:
            values[kind.name + '.missing'] = values[kind.name + '.undeclared'] = 'error: ' + outcome.error[:100]
            continue
        values[kind.name + '.missing'] = [e.name for e in outcome.missing]
        values[kind.name + '.undeclared'] = outcome.undeclared
    return values


def slug(text: str) -> str:
    """Lower-case letters and digits joined by dashes, for generated recipe names."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def pending(setup, state: Dict[str, object]) -> List[Pending]:
    """Recipes generated from a snapshot: one per missing entry a person must install (App Store, downloads, sudo,
    login items, extensions; per kind for apt and snap), and one per kind with undeclared entries."""
    found: List[Pending] = []
    for kind in kinds_for(setup.profile):
        missing = state.get('declared.%s.missing' % kind.name)
        if kind.manual and isinstance(missing, list) and missing:
            entries = [e for e in load(setup, kind) if not e.allowed and e.name in missing and e.source in MANUAL_SOURCES]
            for subject, action in kind.hint(entries):
                found.append(Pending('install-%s-%s' % (kind.name, slug(subject)), 'Install %s (%s)' % (subject, kind.name),
                                     [action, 'converge sync']))
        if isinstance(state.get('declared.%s.undeclared' % kind.name), list) and state['declared.%s.undeclared' % kind.name]:  # a str is an error
            found.append(adopt_recipe(kind))
    return found


def adopt_recipe(kind: Kind) -> Pending:
    """Decide about entries present here that setup/declared/<kind>.txt does not list."""
    return Pending('adopt-' + kind.name, 'Declare or adopt %s' % kind.name,
                   ['converge status --all (lists the undeclared %s)' % kind.name,
                    'Add the ones wanted everywhere to ~/.config/yadm/setup/declared/' + kind.file,
                    'converge adopt %s (allows the rest)' % kind.name])


# --- converge adopt -------------------------------------------------------------------------------------------------

def adopt(setup, kind_name: str) -> int:
    """`converge adopt KIND`: append this machine's undeclared entries as `allowed` under a dated comment (the next
    sync commits and pushes the file); KIND `extras` allows brew extras in extras.txt instead."""
    if kind_name == 'extras':
        import sync_mac
        return sync_mac.adopt_extras(setup, setup.machine_class(), Path('/Applications'))
    kind = KINDS.get(kind_name)
    if kind is None:
        raise RuntimeError('converge adopt: unknown kind %s (kinds: extras, %s)' % (kind_name, ', '.join(KINDS)))
    if setup.profile not in kind.profiles:
        raise RuntimeError('%s are declared on %s machines only' % (kind_name, ', '.join(kind.profiles)))
    outcome = check(setup, kind, setup.machine_class())
    if outcome.error:
        raise RuntimeError('%s: %s' % (kind_name, outcome.error))
    if not outcome.undeclared:
        setup.say('Nothing to adopt: every %s entry here is declared in setup/%s/%s' % (kind_name, DECLARED_DIR, kind.file))
        return 0
    lines = [allowed_line(kind, name) for name in outcome.undeclared]
    for line in lines:
        setup.say(('  Would allow ' if setup.args.plan else '  Allow ') + line)
    if setup.args.plan:
        return 0
    path = setup.assets / DECLARED_DIR / kind.file
    with path.open('a') as stream:
        stream.write('# %s, adopted %s\n%s\n' % (setup.machine_class(), date.today(), '\n'.join(lines)))
    setup.say('%d entries added to %s; the next sync commits and pushes it. Drop `allowed` from any wanted everywhere.'
              % (len(lines), path))
    return 0


def allowed_line(kind: Kind, name: str) -> str:
    """A declaration line allowing `name`; apps also need a source."""
    return '%s  source:manual  allowed' % name if 'source' in kind.keys else '%s  allowed' % name
