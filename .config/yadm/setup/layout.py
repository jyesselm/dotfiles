"""Pure helpers: the home-directory layout manifest and the portability scan."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

PROFILES = {'mac', 'linux', 'cluster'}
CLASSES = {'laptop', 'studio', 'linux', 'cluster'}
STANDARD_TOP_LEVEL = {'Desktop', 'Documents', 'Downloads', 'Library', 'Movies', 'Music', 'Pictures',
                      'Public', 'Applications', 'go', 'micromamba', 'Zotero'}
# Written as (parent, user) pairs so this file does not trip its own scan.
HOMES = [('/Users', 'jyesselman2'), ('/home', 'yesselman'), ('/home', 'jyesselm')]
HOME_RE = re.compile('(' + '|'.join(re.escape(a + '/' + b) for a, b in HOMES) + r')(?![\w.-])')
KNOWN_ABSOLUTE = {
    '.config/iterm2/com.googlecode.iterm2.plist': 'per-Mac iTerm prefs',
    'Library/LaunchAgents/com.yesselman.search-cli-prewarm.plist##class.laptop': 'launchd does not expand ~',
}
MAX_SCAN_BYTES = 2 * 1024 * 1024


@dataclass
class LayoutEntry:
    """One directory from layout.txt; create=False means report only."""
    path: str
    create: bool = True


@dataclass
class LayoutReport:
    """What the layout phase did and saw."""
    created: List[str] = field(default_factory=list)
    expected: List[str] = field(default_factory=list)
    unplanned: List[str] = field(default_factory=list)


def _parse_line(number: int, line: str) -> Tuple[str, dict, bool]:
    """Return (path, filters, check) for one manifest line."""
    path, *tokens = line.split()
    if path.startswith(('/', '~')) or '..' in path.split('/'):
        raise ValueError('layout.txt line %d: path must be relative to $HOME: %s' % (number, path))
    filters: dict = {}
    check = False
    for token in tokens:
        key, _, value = token.partition(':')
        if token == 'check':
            check = True
        elif (key, value) in {('profile', v) for v in PROFILES} | {('class', v) for v in CLASSES}:
            filters[key] = value
        else:
            raise ValueError('layout.txt line %d: unknown token %r' % (number, token))
    return path.rstrip('/'), filters, check


def parse_layout(text: str, profile: Optional[str], machine_class: Optional[str]) -> List[LayoutEntry]:
    """Entries matching profile/class; None for both disables filtering."""
    entries = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        path, filters, check = _parse_line(number, line)
        wanted = {'profile': profile, 'class': machine_class}
        if profile is None and machine_class is None or all(wanted[k] == v for k, v in filters.items()):
            entries.append(LayoutEntry(path, not check))
    return entries


def missing_dirs(root: Path, entries: List[LayoutEntry]) -> List[LayoutEntry]:
    """Entries whose directory is absent (a symlink to a directory counts as present)."""
    return [e for e in entries if not (Path(root) / e.path).is_dir()]


def unplanned_entries(root: Path, entries: List[LayoutEntry]) -> List[str]:
    """Sorted visible top-level names that are neither standard nor in the manifest."""
    planned = {e.path.split('/')[0] for e in entries}
    names = [p.name for p in Path(root).iterdir() if not p.name.startswith('.')]
    return sorted(n for n in names if n not in STANDARD_TOP_LEVEL and n not in planned)


def is_scannable(path: Path) -> bool:
    """True for regular, non-symlink files small enough to scan."""
    return path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_SCAN_BYTES


def _scan(path: Path) -> List[int]:
    """Line numbers in a text file that contain a literal home path."""
    data = path.read_bytes()
    if b'\0' in data:
        return []
    text = data.decode('utf-8', errors='replace')
    return [n for n, line in enumerate(text.splitlines(), 1) if HOME_RE.search(line)]


def find_home_paths(root: Path, ls_files_z: str) -> Tuple[List[str], List[str]]:
    """Return (hits, known) as 'file:line' for literal home paths in tracked files."""
    hits: List[str] = []
    known: List[str] = []
    for name in filter(None, ls_files_z.split('\0')):
        path = Path(root) / name
        if not is_scannable(path):
            continue
        found = ['%s:%d' % (name, n) for n in _scan(path)]
        (known if name in KNOWN_ABSOLUTE else hits).extend(found)
    return hits, known
