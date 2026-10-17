"""Daily schedule for dotfiles-setup --sync: a launchd job on Mac, a crontab line on Linux."""
from __future__ import annotations

import os
import plistlib
import shlex
import sys
from pathlib import Path
from typing import List

from sync import STATE_DIR

LABEL = 'com.yesselman.dotfiles-sync'
MARKER = '# dotfiles-sync'
HOUR, MINUTE = 10, 0
PATH_TAIL = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'


def interpreter(profile: str) -> str:
    """Stable interpreter for the schedule (system Python on Mac, which is 3.9)."""
    if profile == 'mac' and Path('/usr/bin/python3').exists():
        return '/usr/bin/python3'
    return sys.executable


def _command(root: Path, python: str) -> List[str]:
    """The sync command line."""
    return [python, str(Path(root) / '.config/yadm/setup/setup.py'), '--sync']


def _path_env(root: Path) -> str:
    """PATH for a scheduler that starts with almost none."""
    return '%s/.local/bin:%s' % (root, PATH_TAIL)


def launchd_plist(root: Path, python: str) -> dict:
    """LaunchAgent content: daily at 10:00, also at load; launchd runs a missed slot on wake."""
    log = str(Path(root) / STATE_DIR / 'sync.log')
    return {
        'Label': LABEL,
        'ProgramArguments': _command(root, python),
        'StartCalendarInterval': {'Hour': HOUR, 'Minute': MINUTE},
        'RunAtLoad': True,
        'ProcessType': 'Background',
        'Nice': 10,
        'StandardOutPath': log,
        'StandardErrorPath': log,
        'EnvironmentVariables': {'PATH': _path_env(root), 'GIT_TERMINAL_PROMPT': '0', 'GH_PROMPT_DISABLED': '1'},
    }


def cron_lines(root: Path, python: str, profile: str) -> List[str]:
    """Daily crontab line; Linux workstations also run at boot (cluster nodes do not)."""
    log = str(Path(root) / STATE_DIR / 'sync.log')
    command = 'PATH=%s GH_PROMPT_DISABLED=1 %s >> %s 2>&1 %s' % (
        shlex.quote(_path_env(root)), shlex.join(_command(root, python)), shlex.quote(log), MARKER)
    lines = ['%d %d * * * %s' % (MINUTE, HOUR, command)]
    if profile == 'linux':
        lines.append('@reboot ' + command)
    return lines


def merge_crontab(existing: str, lines: List[str]) -> str:
    """Replace only our marked lines; keep everything else."""
    kept = [line for line in existing.splitlines() if MARKER not in line]
    return '\n'.join(kept + lines) + '\n'


def _plist_path(root: Path) -> Path:
    """Where the LaunchAgent lives."""
    return Path(root) / 'Library/LaunchAgents' / (LABEL + '.plist')


def _install_launchd(setup) -> int:
    """Write the LaunchAgent and (re)load it."""
    plist = _plist_path(setup.root)
    data = launchd_plist(setup.root, interpreter(setup.profile))
    domain = 'gui/%d' % os.getuid()
    if setup.args.plan:
        setup.say(plistlib.dumps(data).decode())
        setup.say('  $ launchctl bootout %s/%s  (ignored if not loaded)' % (domain, LABEL))
    else:
        plist.parent.mkdir(parents=True, exist_ok=True)
        (Path(setup.root) / STATE_DIR).mkdir(parents=True, exist_ok=True)
        with open(plist, 'wb') as stream:
            plistlib.dump(data, stream)
        setup.read(['launchctl', 'bootout', '%s/%s' % (domain, LABEL)])
    setup.run(['launchctl', 'bootstrap', domain, plist])
    setup.say('  A first sync starts now (RunAtLoad), then daily at %02d:%02d.' % (HOUR, MINUTE))
    return 0


def _install_cron(setup) -> int:
    """Merge our line into the user's crontab, or skip when cron is unavailable."""
    existing = setup.read(['crontab', '-l'])
    if existing.returncode == 127 or (existing.returncode and 'no crontab' not in existing.stderr.lower()):
        note = existing.stderr.strip()[:100] or 'no crontab command'
        setup.say('  crontab unavailable here; schedule skipped (%s)' % note)
        return 0
    current = existing.stdout if existing.returncode == 0 else ''
    merged = merge_crontab(current, cron_lines(setup.root, interpreter(setup.profile), setup.profile))
    if setup.args.plan:
        setup.say(merged)
        return 0
    (Path(setup.root) / STATE_DIR).mkdir(parents=True, exist_ok=True)
    setup.run(['crontab', '-'], input=merged, text=True)
    return 0


def install(setup) -> int:
    """Install the daily schedule for this platform; --plan only prints."""
    return _install_launchd(setup) if setup.profile == 'mac' else _install_cron(setup)


def is_installed(setup) -> bool:
    """Whether the daily schedule exists on this machine."""
    if setup.profile == 'mac':
        return _plist_path(setup.root).exists()
    return MARKER in setup.read(['crontab', '-l']).stdout
