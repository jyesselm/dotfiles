"""Converge the Search GUI binding and resident process after checkout updates."""
import hashlib
import json
import os
import plistlib
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import time

DESCRIPTION = 'F4 -> Search launcher (s gui)'
OLD_DESCRIPTION = 'Cmd+, -> search-cli desktop launcher (s gui)'


def f4_rule():
    return {'description': DESCRIPTION, 'manipulators': [
        {'type': 'basic', 'from': {**key, 'modifiers': {'optional': ['fn', 'caps_lock']}},
         'to': [{'shell_command': '"$HOME/.local/bin/s" gui'}]}
        for key in ({'key_code': 'f4'}, {'apple_vendor_keyboard_key_code': 'spotlight'})]}


def configure_f4(path, plan=False):
    if not path.exists():
        return 'warn', 'Karabiner configuration missing; open Karabiner once, then rerun converge'
    data = json.loads(path.read_text())
    profile = next((p for p in data.get('profiles', []) if p.get('selected')), None)
    if profile is None:
        return 'warn', 'No selected Karabiner profile; select one then rerun converge'
    rules = profile.setdefault('complex_modifications', {}).setdefault('rules', [])
    desired = [f4_rule()] + [r for r in rules if r.get('description') not in (DESCRIPTION, OLD_DESCRIPTION)]
    if rules == desired:
        return 'ok', 'F4 and Spotlight key already open Search'
    if plan:
        return 'ok', 'would bind F4 and Spotlight key to Search (preserving other rules)'
    backup = path.with_name(path.name + '.before-converge-search-' + str(time.time_ns()))
    shutil.copy2(path, backup)
    profile['complex_modifications']['rules'] = desired
    path.write_text(json.dumps(data, indent=4) + '\n')
    return 'changed', 'F4 and Spotlight key now open Search; previous config backed up'


def retire_alfred_binding(root, plan=False):
    prefs = root / 'Library/Application Support/Alfred/prefs.json'
    if not prefs.exists():
        return 'ok', 'No Alfred preferences to migrate'
    current = json.loads(prefs.read_text()).get('current')
    if not current:
        return 'ok', 'No active Alfred sync folder'
    folder = Path(current.replace('~/', str(root) + '/', 1))
    changed = 0
    for path in (folder / 'workflows').glob('*/info.plist'):
        raw = path.read_bytes()
        data = plistlib.loads(raw)
        if data.get('name') != 'Search CLI Launcher':
            continue
        updates = []
        for obj in data.get('objects', []):
            config = obj.get('config', {})
            if obj.get('type') == 'alfred.workflow.trigger.hotkey' and config.get('hotkey') == 43 and config.get('hotmod') == 1048576:
                updates.append(config)
        if not updates:
            continue
        changed += 1
        if not plan:
            backup = path.with_name('info.before-search-f4-' + str(time.time_ns()) + '.plist')
            shutil.copy2(path, backup)
            for config in updates:
                config.update(hotkey=0, hotmod=0, hotstring='')
            path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY if raw.startswith(b'bplist') else plistlib.FMT_XML))
    if changed:
        return ('ok' if plan else 'changed'), ('would clear' if plan else 'cleared') + ' obsolete Alfred Search Cmd+, binding; workflow preserved'
    return 'ok', 'No obsolete Alfred Search binding'


def source_digest(checkout):
    digest = hashlib.sha256()
    for path in sorted((checkout / 'src/search_cli').rglob('*')):
        if path.is_file() and path.suffix in ('.py', '.png', '.icns') and '__pycache__' not in path.parts:
            digest.update(str(path.relative_to(checkout)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def is_gui_command(command):
    """Match Search GUI only, never an indexer or terminal search."""
    try:
        args = shlex.split(command)
    except ValueError:
        return False
    return any(Path(part).name in ('s', 'search') and args[i+1:i+2] == ['gui']
               for i, part in enumerate(args)) or any(
        args[i:i+3] in (['-m', 'search_cli.cli', 'gui'], ['-m', 'search_cli', 'gui'])
        for i in range(len(args)))


def resident_pid(lock, uid):
    if not lock.exists():
        return None
    try:
        pid = int(lock.read_text().splitlines()[0])
    except (ValueError, IndexError):
        return None
    if pid <= 1:
        return None
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'uid=', '-o', 'command='], capture_output=True, text=True, check=False)
    fields = result.stdout.strip().split(None, 1)
    if result.returncode or len(fields) != 2 or fields[0] != str(uid) or not is_gui_command(fields[1]):
        return None
    return pid


def refresh_resident(checkout, marker, plan=False, lock=None):
    digest = source_digest(checkout)
    if marker.exists() and marker.read_text().strip() == digest:
        return 'ok', 'Search GUI code already refreshed'
    lock = lock or Path(tempfile.gettempdir()) / ('search-cli-gui-%d.lock' % os.getuid())
    pid = resident_pid(lock, os.getuid())
    if plan:
        return 'ok', 'would retire old Search GUI process and load current code on next F4'
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        for _ in range(50):
            if resident_pid(lock, os.getuid()) != pid:
                break
            time.sleep(.1)
        else:
            return 'warn', 'Old Search GUI did not exit; quit it before pressing F4'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(digest + '\n')
    return 'changed', 'Search GUI refreshed; next F4 loads the current checkout'


def desktop(setup):
    if setup.profile != 'mac':
        return 'skipped', 'Mac Search launcher setup is not applicable on this platform'
    checkout = setup.checkout('s')
    if not (checkout / 'src/search_cli/desktop_ui.py').exists():
        return 'warn', 'Search desktop checkout missing; run converge setup --search'
    states, details = [], []
    for state, detail in (
        configure_f4(setup.root / '.config/karabiner/karabiner.json', setup.args.plan),
        refresh_resident(checkout, setup.root / '.local/state/dotfiles/sync/search-gui.sha256', setup.args.plan),
    ):
        states.append(state)
        details.append(detail)
    if states[0] != 'warn':
        state, detail = retire_alfred_binding(setup.root, setup.args.plan)
        states.append(state)
        details.append(detail)
    return ('warn' if 'warn' in states else 'changed' if 'changed' in states else 'ok'), '; '.join(details)
