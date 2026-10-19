"""Linux hotkeys and look for converge sync: Toshy slices + GNOME dconf files from ~/.config/hotkeys/linux/."""
from __future__ import annotations

import configparser
import re
import time
from datetime import datetime
from typing import Dict, List, Tuple

HOTKEYS = '.config/hotkeys/linux'
TOSHY = '.config/toshy/toshy_config.py'
SERVICE = 'toshy-config.service'
SLICE = re.compile(r'^### toshy-slice: (\w+)\s*$', re.M)


def user_slices(text: str) -> Dict[str, str]:
    """{slice name: body} from toshy_user.py; text before the first marker is a header comment."""
    parts = SLICE.split(text)
    return {name: body.strip('\n') for name, body in zip(parts[1::2], parts[2::2])}


def splice(config: str, slices: Dict[str, str]) -> str:
    """toshy_config.py with each named SLICE_MARK block's contents replaced; ValueError if a marker is missing."""
    for name, body in slices.items():
        block = re.compile(r'(###  SLICE_MARK_START: %s  ###[^\n]*\n)(.*?)(###  SLICE_MARK_END: %s  ###)'
                           % (re.escape(name), re.escape(name)), re.S)
        if not block.search(config):
            raise ValueError('toshy_config.py has no %s slice (Toshy upgraded?)' % name)
        config = block.sub(lambda m: m.group(1) + '\n' + body + '\n\n' + m.group(3), config, count=1)
    return config


def dconf_same(current: str, wanted: str) -> bool:
    """dconf prints 0.35 as 0.34999999999999998, so compare floats by value."""
    try:
        return current == wanted or abs(float(current) - float(wanted)) < 1e-9
    except ValueError:
        return False


def dconf_keys(text: str) -> Dict[str, str]:
    """{'/org/x/key': 'value'} from `dconf load /` keyfiles; a section may repeat across files."""
    parser = configparser.ConfigParser(interpolation=None, delimiters=('=',), comment_prefixes=('#',), strict=False)
    parser.optionxform = str
    parser.read_string(text)
    return {'/%s/%s' % (section, key): value for section in parser.sections() for key, value in parser[section].items()}


def hotkeys(setup) -> Tuple[str, str, List[str]]:
    """(status, summary, details): converge Toshy and GNOME to the tracked files, then check Toshy is running."""
    source, config = setup.root / HOTKEYS, setup.root / TOSHY
    if not (source / 'toshy_user.py').exists():
        return 'skipped', 'no Linux hotkeys tracked', []
    if not config.exists():
        return 'warn', 'Toshy not installed, so Mac shortcuts do nothing', ['install Toshy (see personal-computer-setup docs/ubuntu.md), then converge sync']
    plan, stamp, changed, details = setup.args.plan, datetime.now().strftime('%Y%m%d-%H%M%S'), [], []

    current = config.read_text()
    wanted = splice(current, user_slices((source / 'toshy_user.py').read_text()))
    if wanted != current:
        changed.append('Toshy slices')
        if not plan:
            config.with_name('toshy_config.before-converge.py').write_text(current)
            config.write_text(wanted)
            setup.run(['systemctl', '--user', 'restart', SERVICE])

    dconf = ''.join(f.read_text() + '\n' for f in sorted(source.glob('*.dconf'))).replace("'~/", "'%s/" % setup.root)
    keys = dconf_keys(dconf)
    stale = [key for key, value in keys.items() if not dconf_same(setup.read(['dconf', 'read', key]).stdout.strip(), value)]
    if stale:
        changed.append('%d GNOME keys' % len(stale))
        details += ['dconf: ' + key for key in stale[:10]]
        if not plan:
            backup = setup.root / ('.local/state/dotfiles/dconf-%s.ini' % stamp)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(setup.read_ok(['dconf', 'dump', '/'], 'dconf dump failed'))
            setup.run(['dconf', 'load', '/'], input=dconf, text=True)

    if plan:
        return 'ok', ('would update ' + ', '.join(changed)) if changed else 'up to date', details
    if changed:
        time.sleep(2)  # a config error makes xwaykeyz exit right after start
    if setup.read(['systemctl', '--user', 'is-active', SERVICE]).stdout.strip() != 'active':
        log = setup.read(['journalctl', '--user', '-u', SERVICE, '-n', '15', '--no-pager']).stdout.splitlines()
        return 'warn', 'Toshy is not running', ['previous config: ' + str(config.with_name('toshy_config.before-converge.py'))] + log
    return ('changed', 'updated ' + ', '.join(changed), details) if changed else ('ok', 'Toshy running, keys match', details)
