"""Pure helpers: the home-directory layout manifest and the portability scan."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

PROFILES = {'mac', 'linux', 'cluster'}
CLASSES = {'laptop', 'studio', 'linux', 'cluster', 'server'}
STANDARD_TOP_LEVEL = {'Desktop', 'Documents', 'Downloads', 'Library', 'Movies', 'Music', 'Pictures', 'Public', 'Applications',
                      'Templates', 'Videos',  # XDG names on Linux
                      'go', 'micromamba', 'miniconda3', 'Zotero'}
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
    """One line of layout.txt: a directory to create or link, to check (report only), a glob to ignore
    or a glob whose top-level symlinks are removed on every sync."""
    path: str
    create: bool = True
    ignore: bool = False
    link: Optional[str] = None  # ~-relative symlink target
    unlink: bool = False


@dataclass
class LayoutReport:
    """What the layout phase did and saw."""
    created: List[str] = field(default_factory=list)
    expected: List[str] = field(default_factory=list)
    unplanned: List[str] = field(default_factory=list)
    unlinked: List[str] = field(default_factory=list)


def _home_relative(path: str) -> bool:
    return bool(path) and not path.startswith(('/', '~')) and '..' not in path.split('/')


def manifest_lines(text: str) -> List[Tuple[int, str]]:
    """(line number, content) of every non-blank line with its `#` comment removed: the line format shared by
    layout.txt, extras.txt and setup/declared/*.txt."""
    numbered = [(number, raw.split('#', 1)[0].strip()) for number, raw in enumerate(text.splitlines(), 1)]
    return [(number, line) for number, line in numbered if line]


def split_qualifiers(line: str, flags: Iterable[str]) -> Tuple[str, List[str]]:
    """(entry, qualifiers): the trailing tokens that contain ':' or are one of `flags` qualify the entry;
    everything before them is the entry, which may contain spaces (`Microsoft Word  source:brew`)."""
    tokens = line.split()
    cut = len(tokens)
    while cut > 1 and (':' in tokens[cut - 1] or tokens[cut - 1] in flags):
        cut -= 1
    return ' '.join(tokens[:cut]), tokens[cut:]


def _parse_line(number: int, line: str) -> Tuple[str, dict, bool, bool, Optional[str], bool]:
    """Return (path, filters, check, ignore, link, unlink) for one manifest line."""
    path, *tokens = line.split()
    if not _home_relative(path):
        raise ValueError('layout.txt line %d: path must be relative to $HOME: %s' % (number, path))
    filters: dict = {}
    check = ignore = unlink = False
    link: Optional[str] = None
    for token in tokens:
        key, _, value = token.partition(':')
        if token in ('check', 'ignore', 'unlink'):
            check, ignore, unlink = check or token == 'check', ignore or token == 'ignore', unlink or token == 'unlink'
        elif key in ('profile', 'class') and value and set(value.split(',')) <= (PROFILES if key == 'profile' else CLASSES):
            filters[key] = set(value.split(','))
        elif key == 'link' and _home_relative(value):
            link = value.rstrip('/')
        else:
            raise ValueError('layout.txt line %d: unknown token %r' % (number, token))
    if sum([check, ignore, unlink, bool(link)]) > 1:
        raise ValueError('layout.txt line %d: check, ignore, unlink and link are exclusive' % number)
    if (ignore or unlink) and '/' in path.rstrip('/'):
        raise ValueError('layout.txt line %d: ignore/unlink patterns are top-level names: %s' % (number, path))
    return path.rstrip('/'), filters, check, ignore, link, unlink


def parse_layout(text: str, profile: Optional[str], machine_class: Optional[str]) -> List[LayoutEntry]:
    """Entries matching profile/class; None for both disables filtering."""
    entries = []
    for number, line in manifest_lines(text):
        path, filters, check, ignore, link, unlink = _parse_line(number, line)
        wanted = {'profile': profile, 'class': machine_class}
        if profile is None and machine_class is None or all(wanted[k] in v for k, v in filters.items()):
            entries.append(LayoutEntry(path, not (check or ignore or unlink), ignore or unlink, link, unlink))
    return entries


def missing_dirs(root: Path, entries: List[LayoutEntry]) -> List[LayoutEntry]:
    """Entries whose directory is absent (a symlink to a directory counts as present)."""
    return [e for e in entries if not e.ignore and not (Path(root) / e.path).is_dir()]


def unplanned_entries(root: Path, entries: List[LayoutEntry]) -> List[str]:
    """Sorted visible top-level names that are neither standard, planned nor matched by an ignore glob."""
    planned = {e.path.split('/')[0] for e in entries if not e.ignore}
    ignored = [e.path for e in entries if e.ignore]
    names = [p.name for p in Path(root).iterdir() if not p.name.startswith('.')]
    return sorted(n for n in names if n not in STANDARD_TOP_LEVEL and n not in planned
                  and not any(fnmatch.fnmatchcase(n, pattern) for pattern in ignored))


def stray_links(root: Path, entries: List[LayoutEntry]) -> List[str]:
    """Sorted top-level symlinks matched by an unlink glob; real files and directories never qualify."""
    globs = [e.path for e in entries if e.unlink]
    return sorted(p.name for p in Path(root).iterdir()
                  if p.is_symlink() and any(fnmatch.fnmatchcase(p.name, g) for g in globs))


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
