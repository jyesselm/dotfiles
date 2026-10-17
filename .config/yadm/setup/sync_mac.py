"""Mac phases of converge sync: Brewfile packages and home-made apps."""
from __future__ import annotations

import json
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import date
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from setup import version
from sync import BREW_TIMEOUT, NET_TIMEOUT, PhaseResult

BREWFILES = {
    'laptop': ['Brewfile', 'Brewfile.previews', 'Brewfile.desktop', 'Brewfile.apps'],
    'studio': ['Brewfile', 'Brewfile.previews', 'Brewfile.desktop', 'Brewfile.apps'],
}
TERMINAL_ONLY = ['Brewfile']  # mac with an unknown/unset class
APP_CLASSES = ('laptop', 'studio')
EXTRAS_FILE = 'extras.txt'  # formula:/cask: entries allowed on some computers without being wanted everywhere
APP_KEYS = ('name', 'bundle_id', 'repo', 'bundle', 'assets')
SEARCH_APP, SEARCH_APP_ID = 'Search CLI.app', 'com.yesselman.search-cli.gui'
SEARCH_LAUNCHER = '''#!/bin/zsh
# Written by converge sync: opens the search-cli desktop launcher through the uv-installed `s`.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$HOME"
mkdir -p "$HOME/Library/Logs"
exec "$HOME/.local/bin/s" gui >> "$HOME/Library/Logs/search-cli-gui.log" 2>&1
'''


@dataclass
class Manifest:
    """Entries of a merged Brewfile."""
    formulae: List[str] = field(default_factory=list)
    casks: List[str] = field(default_factory=list)
    mas_ids: List[int] = field(default_factory=list)
    present: Dict[str, str] = field(default_factory=dict)  # cask token -> "# present:" path


def merge_brewfiles(paths: List[Path]) -> str:
    """Join Brewfiles under '# --- name ---' headers, dropping duplicate entry lines."""
    seen = set()
    parts = []
    for path in paths:
        lines = ['# --- %s ---' % Path(path).name]
        for line in Path(path).read_text().splitlines():
            is_entry = bool(line.strip()) and not line.lstrip().startswith('#')
            if is_entry and line in seen:
                continue
            if is_entry:
                seen.add(line)
            lines.append(line)
        parts.append('\n'.join(lines))
    return '\n'.join(parts) + '\n'


def parse_brewfile(text: str) -> Manifest:
    """Collect brew/cask/mas entries and '# present: <path>' hints."""
    manifest = Manifest()
    for line in text.splitlines():
        brew = re.match(r'^brew "([^"]+)"', line)
        cask = re.match(r'^cask "([^"]+)"', line)
        mas = re.match(r'^mas "[^"]+",\s*id:\s*(\d+)', line)
        if brew:
            manifest.formulae.append(brew.group(1))
        elif cask:
            manifest.casks.append(cask.group(1))
            hint = re.search(r'#\s*present:\s*(.+?)\s*$', line)
            if hint:
                manifest.present[cask.group(1)] = hint.group(1)
        elif mas:
            manifest.mas_ids.append(int(mas.group(1)))
    return manifest


def _normal(name: str) -> str:
    """Drop the tap prefix and any @version suffix."""
    return name.rsplit('/', 1)[-1].split('@', 1)[0]


def parse_extras(text: str) -> set:
    """Allowed 'formula:name' / 'cask:name' entries of extras.txt; '#' starts a comment."""
    entries = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        kind, _, name = line.partition(':')
        if kind not in ('formula', 'cask') or not name:
            raise ValueError('%s line %d: expected formula:<name> or cask:<name>, got %r' % (EXTRAS_FILE, number, line))
        entries.add(kind + ':' + _normal(name))
    return entries


def brew_extras(leaves: List[str], installed_casks: List[str], manifest: Manifest, allowed=frozenset()) -> List[str]:
    """Installed-on-request formulae/casks neither in the manifest nor allowed by extras.txt (report-only)."""
    wanted_formulae = {_normal(n) for n in manifest.formulae}
    wanted_casks = {_normal(n) for n in manifest.casks}
    extras = ['formula:' + _normal(n) for n in leaves if _normal(n) not in wanted_formulae]
    extras += ['cask:' + _normal(n) for n in installed_casks if _normal(n) not in wanted_casks]
    return sorted(set(extras) - set(allowed))


def cask_app_names(info_json: dict) -> Dict[str, List[str]]:
    """Map each cask token to the .app names in its 'app' artifacts."""
    names: Dict[str, List[str]] = {}
    for cask in info_json.get('casks', []):
        apps: List[str] = []
        for artifact in cask.get('artifacts', []):
            if isinstance(artifact, dict):
                apps += [a for a in artifact.get('app', []) if isinstance(a, str)]
        names[cask['token']] = apps
    return names


def present_outside_brew(manifest: Manifest, installed_casks: List[str],
                         app_names: Dict[str, List[str]], applications: Path) -> List[str]:
    """Manifest casks not installed by brew whose app (or hint path) already exists."""
    found = []
    for token in manifest.casks:
        if token in installed_casks:
            continue
        paths = [Path(applications) / app for app in app_names.get(token, [])]
        if token in manifest.present:
            paths.append(Path(manifest.present[token]))
        if any(p.exists() for p in paths):
            found.append(token)
    return found


def _lines(setup, argv: List[str]) -> List[str]:
    """Output words of a read-only brew command; plan mode tolerates a missing brew."""
    if setup.args.plan and not setup.find(argv[0]):
        return []
    return setup.read_ok(argv, ' '.join(map(str, argv[:3])) + ' failed').split()


def _cask_apps(setup, brew: str, missing: List[str]) -> Dict[str, List[str]]:
    """App names for casks not installed by brew (one `brew info` call)."""
    if not missing or (setup.args.plan and not setup.find(brew)):
        return {}
    out = setup.read_ok([brew, 'info', '--cask', '--json=v2'] + missing, 'brew info failed')
    return cask_app_names(json.loads(out))


def _inventory(setup, brew: str, manifest: Manifest, applications: Path) -> Tuple[List[str], List[str]]:
    """Return (casks to skip because present outside brew, extras not allowed by extras.txt)."""
    casks = _lines(setup, [brew, 'list', '--cask', '-1'])
    leaves = _lines(setup, [brew, 'leaves', '--installed-on-request'])
    app_names = _cask_apps(setup, brew, [c for c in manifest.casks if c not in casks])
    extras_file = setup.assets / EXTRAS_FILE
    allowed = parse_extras(extras_file.read_text() if extras_file.exists() else '')  # absent until first committed
    return (present_outside_brew(manifest, casks, app_names, applications),
            brew_extras(leaves, casks, manifest, allowed))


def _manifest(setup, machine_class: str) -> Tuple[List[str], str]:
    """(Brewfile names for this class, their merged text)."""
    names = BREWFILES.get(machine_class, TERMINAL_ONLY)
    return names, merge_brewfiles([setup.assets / n for n in names])


def _bundle_install(setup, brew: str, text: str, skip: List[str]) -> None:
    """brew bundle install of the merged Brewfile, skipping casks already present."""
    env = dict(setup.env, HOMEBREW_BUNDLE_CASK_SKIP=' '.join(skip))
    command = [brew, 'bundle', 'install', '--no-upgrade', '--file']
    if setup.args.plan:
        setup.say('  HOMEBREW_BUNDLE_CASK_SKIP=' + ' '.join(skip))
        setup.run(command + ['<merged Brewfiles>'], env=env, timeout=BREW_TIMEOUT)
        return
    with tempfile.TemporaryDirectory(prefix='dotfiles-brew-') as tmp:
        merged = Path(tmp) / 'Brewfile'
        merged.write_text(text)
        # DEVNULL: pkg casks that need sudo fail fast instead of hanging under launchd.
        setup.run(command + [merged], env=env, stdin=subprocess.DEVNULL, timeout=BREW_TIMEOUT)


def packages(setup, machine_class: str, applications: Path) -> PhaseResult:
    """Install missing Brewfile entries for this class; report (never remove) extras."""
    brew = setup.find('brew')
    if not brew and not setup.args.plan:
        raise RuntimeError('Install Homebrew from https://brew.sh, then rerun.')
    known = machine_class in BREWFILES
    names, text = _manifest(setup, machine_class)
    skip, extras = _inventory(setup, brew or 'brew', parse_brewfile(text), applications)
    _bundle_install(setup, brew or 'brew', text, skip)
    summary = '%d extras in no Brewfile or %s (not removed), %d casks present outside Homebrew, %d Brewfiles' % (
        len(extras), EXTRAS_FILE, len(skip), len(names))
    if not known:
        summary += '; class unknown, set: yadm config local.class laptop|studio'
    status = 'warn' if extras or not known else 'ok'
    return PhaseResult(status, summary, extras + ['present:' + t for t in skip])


def adopt_extras(setup, machine_class: str, applications: Path) -> int:
    """Allow this computer's current extras by appending them to extras.txt; the next sync commits and pushes it."""
    if setup.profile != 'mac':
        raise RuntimeError('--adopt-extras reads Homebrew; run it on a Mac.')
    brew = setup.find('brew')
    if not brew:
        raise RuntimeError('brew not on PATH')
    path = setup.assets / EXTRAS_FILE
    _, extras = _inventory(setup, brew, parse_brewfile(_manifest(setup, machine_class)[1]), applications)
    if not extras:
        setup.say('Nothing to adopt: every installed package is in a Brewfile or ' + EXTRAS_FILE)
        return 0
    for extra in extras:
        setup.say(('  Would allow ' if setup.args.plan else '  Allow ') + extra)
    if setup.args.plan:
        return 0
    with path.open('a') as stream:
        stream.write('# %s, adopted %s\n%s\n' % (machine_class, date.today(), '\n'.join(extras)))
    setup.say('%d entries added to %s; the next sync commits and pushes it. Move anything wanted on every Mac into a Brewfile instead.'
              % (len(extras), path))
    return 0


def load_apps(path: Path) -> List[dict]:
    """Read apps.json, validating the format and required keys."""
    data = json.loads(Path(path).read_text())
    if data.get('format') != 1:
        raise ValueError('apps.json: unsupported format')
    for app in data['apps']:
        missing = [k for k in APP_KEYS if k not in app]
        if missing:
            raise ValueError('apps.json: %s missing %s' % (app.get('name', '?'), ', '.join(missing)))
    return data['apps']


def installed_version(app_path: Path, bundle_id: str) -> Optional[str]:
    """Version of an installed bundle; None if absent; RuntimeError if it is someone else's app."""
    plist = Path(app_path) / 'Contents/Info.plist'
    if not Path(app_path).exists():
        return None
    info = plistlib.loads(plist.read_bytes())
    if info.get('CFBundleIdentifier') != bundle_id:
        raise RuntimeError('%s is a different app (%s); left untouched' % (app_path, info.get('CFBundleIdentifier')))
    return str(info.get('CFBundleShortVersionString') or info.get('CFBundleVersion') or '0')


def needs_upgrade(installed: Optional[str], tag: str) -> bool:
    """True when the release tag is newer than the installed version."""
    return installed is None or version(tag) > version(installed)


def replace_bundle(new: Path, path: Path) -> None:
    """Swap in the new bundle. The old one waits beside the target (same volume) until success."""
    path = Path(path)
    had_old = path.exists()
    stash = path.with_name('.' + path.name + '.old-' + uuid.uuid4().hex[:8])
    if had_old:  # leftovers of an earlier interrupted swap; only safe to drop while the live app exists
        for leftover in path.parent.glob('.' + path.name + '.old-*'):
            shutil.rmtree(leftover, ignore_errors=True)
    placing = False
    try:
        if had_old:
            shutil.move(str(path), str(stash))
        placing = True
        shutil.move(str(new), str(path))
    except BaseException:
        if placing and path.exists():  # a partly copied new bundle, ours to remove
            shutil.rmtree(path, ignore_errors=True)
        if had_old and stash.exists():
            shutil.move(str(stash), str(path))
        raise
    if had_old:
        shutil.rmtree(stash, ignore_errors=True)


def install_release(setup, app: dict, tag: str, path: Path) -> None:
    """Download app['asset'] from a release, unpack with ditto (keeps symlinks) and replace the bundle."""
    asset = app['asset']
    download = ['gh', 'release', 'download', tag, '--repo', app['repo'], '--pattern', asset, '--dir']
    quarantine = ['xattr', '-dr', 'com.apple.quarantine', path]
    if setup.args.plan:
        setup.run(download + ['<tmp>'])
        setup.run(['ditto', '-x', '-k', '<tmp>/' + asset, '<tmp>/unpacked'])
        setup.run(quarantine)
        return
    with tempfile.TemporaryDirectory(prefix='dotfiles-app-') as tmp:
        work = Path(tmp)
        setup.run(download + [work], timeout=NET_TIMEOUT)
        setup.run(['ditto', '-x', '-k', work / asset, work / 'unpacked'], timeout=NET_TIMEOUT)
        bundles = list((work / 'unpacked').glob('*.app'))
        if len(bundles) != 1:
            raise RuntimeError('%s: expected one .app in %s, found %d' % (app['name'], asset, len(bundles)))
        found = installed_version(bundles[0], app['bundle_id'])
        if needs_upgrade(found, tag):
            raise RuntimeError('%s: downloaded bundle is %s, older than release %s' % (app['name'], found, tag))
        replace_bundle(bundles[0], path)
        setup.run(quarantine, timeout=NET_TIMEOUT)


def _latest_tag(setup, repo: str) -> str:
    """Latest release tag of a GitHub repo."""
    argv = ['gh', 'release', 'view', '--repo', repo, '--json', 'tagName', '-q', '.tagName']
    return setup.read_ok(argv, 'gh release view %s failed' % repo).strip()


def sync_app(setup, app: dict, applications: Path, arch: str) -> Tuple[str, str]:
    """Bring one app to its latest release; return (detail line, ok|changed|warn)."""
    name, path = app['name'], Path(applications) / app['bundle']
    installed = installed_version(path, app['bundle_id'])
    if not app['assets']:
        hint = 'build locally: ' + app.get('build', '?')
        return '%s %s: no releases; %s' % (name, installed or 'absent', hint), 'warn'
    if arch not in app['assets']:
        raise RuntimeError('%s has no %s release asset' % (name, arch))
    tag = _latest_tag(setup, app['repo'])
    if not needs_upgrade(installed, tag):
        return '%s %s up to date' % (name, installed), 'ok'
    label = '%s %s -> %s' % (name, installed or 'absent', tag.lstrip('v'))
    if installed and setup.read(['pgrep', '-f', str(path / 'Contents/MacOS')]).returncode == 0:
        return '%s available; quit %s and rerun sync' % (label, name), 'warn'
    install_release(setup, dict(app, asset=app['assets'][arch]), tag, path)
    if setup.args.plan:
        return label + ' (would install)', 'ok'
    return label + ' installed', 'changed'


def search_app(setup, applications: Path) -> Tuple[str, str]:
    """Write the Search CLI bundle (a launcher for `s gui`, icon from the search-cli checkout); (detail, ok|changed|warn)."""
    icon = setup.checkout('s') / 'src/search_cli/assets/search-lens.icns'
    if not icon.exists():
        return 'Search CLI: search-cli checkout or its icon missing; launcher left alone', 'warn'
    bundle = Path(applications) / SEARCH_APP
    info = {'CFBundleExecutable': 'search-cli', 'CFBundleIconFile': 'search-lens.icns', 'CFBundleIdentifier': SEARCH_APP_ID,
            'CFBundleName': 'Search CLI', 'CFBundlePackageType': 'APPL', 'CFBundleVersion': '3', 'NSHighResolutionCapable': True}
    files = {'Contents/Info.plist': plistlib.dumps(info, sort_keys=True), 'Contents/MacOS/search-cli': SEARCH_LAUNCHER.encode(),
             'Contents/Resources/search-lens.icns': icon.read_bytes()}
    stale = [rel for rel, data in files.items() if not (bundle / rel).exists() or (bundle / rel).read_bytes() != data]
    if not stale:
        return 'Search CLI launcher up to date', 'ok'
    label = 'Search CLI launcher %s' % ('updated' if bundle.exists() else 'installed')
    if setup.args.plan:
        return '%s (would write %s)' % (label, ', '.join(stale)), 'ok'
    for rel in stale:
        (bundle / rel).parent.mkdir(parents=True, exist_ok=True)
        (bundle / rel).write_bytes(files[rel])
    (bundle / 'Contents/MacOS/search-cli').chmod(0o755)
    return label, 'changed'


def apps(setup, machine_class: str, applications: Path) -> PhaseResult:
    """Install or upgrade the home-made apps listed in apps.json, then the Search CLI launcher."""
    if setup.profile != 'mac':
        return PhaseResult('skipped', 'apps are installed on macOS only')
    if machine_class not in APP_CLASSES:
        return PhaseResult('skipped', 'class %s has no apps; set: yadm config local.class laptop' % machine_class)
    details, states = [], []
    jobs = [(app['name'], lambda app=app: sync_app(setup, app, applications, platform.machine())) for app in load_apps(setup.assets / 'apps.json')]
    jobs.append(('Search CLI', lambda: search_app(setup, applications)))
    for name, job in jobs:
        try:
            detail, state = job()
        except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as exc:
            detail, state = '%s: %s' % (name, exc), 'failed'
        details.append(detail)
        states.append(state)
    status = next((s for s in ('failed', 'changed', 'warn') if s in states), 'ok')
    issues = [d.split(':')[0] for d, state in zip(details, states) if state != 'ok']  # the detail keeps the full text
    return PhaseResult(status, '%d apps checked' % len(details) + ('; ' + '; '.join(issues) if issues else ''), details)
