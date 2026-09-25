#!/usr/bin/env python3
"""Save selected macOS preferences; preview or explicitly restore them."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile
import uuid

# Deliberately exclude accounts, recent files, Dock bookmarks, licenses, and device IDs.
GLOBAL = '''AppleInterfaceStyle AppleInterfaceStyleSwitchesAutomatically AppleAccentColor
AppleHighlightColor AppleAquaColorVariant AppleShowScrollBars AppleActionOnDoubleClick
AppleMiniaturizeOnDoubleClick AppleKeyboardUIMode ApplePressAndHoldEnabled KeyRepeat
InitialKeyRepeat AppleShowAllExtensions NSAutomaticCapitalizationEnabled
NSAutomaticPeriodSubstitutionEnabled NSAutomaticQuoteSubstitutionEnabled
NSAutomaticDashSubstitutionEnabled NSAutomaticSpellingCorrectionEnabled
NSAutomaticTextCompletionEnabled NSAllowContinuousSpellChecking
NSNavPanelExpandedStateForSaveMode NSNavPanelExpandedStateForSaveMode2
PMPrintingExpandedStateForPrint PMPrintingExpandedStateForPrint2 NSUserKeyEquivalents
com.apple.keyboard.fnState com.apple.mouse.scaling com.apple.scrollwheel.scaling
com.apple.swipescrolldirection com.apple.trackpad.scaling com.apple.trackpad.forceClick
com.apple.springing.enabled com.apple.springing.delay com.apple.sound.beep.flash'''.split()
TRACKPAD = '''Clicking DragLock Dragging ActuateDetents FirstClickThreshold SecondClickThreshold
ForceSuppressed TrackpadCornerSecondaryClick TrackpadFiveFingerPinchGesture
TrackpadFourFingerHorizSwipeGesture TrackpadFourFingerPinchGesture TrackpadFourFingerVertSwipeGesture
TrackpadHandResting TrackpadHorizScroll TrackpadMomentumScroll TrackpadPinch TrackpadRightClick
TrackpadRotate TrackpadScroll TrackpadThreeFingerDrag TrackpadThreeFingerHorizSwipeGesture
TrackpadThreeFingerTapGesture TrackpadThreeFingerVertSwipeGesture TrackpadTwoFingerDoubleTapGesture
TrackpadTwoFingerFromRightEdgeSwipeGesture USBMouseStopsTrackpad'''.split()
MOUSE = '''MouseButtonDivision MouseButtonMode MouseHorizontalScroll MouseMomentumScroll
MouseOneFingerDoubleTapGesture MouseTwoFingerDoubleTapGesture MouseTwoFingerHorizSwipeGesture
MouseVerticalScroll'''.split()
ALLOW = {
    'NSGlobalDomain': GLOBAL,
    'com.apple.dock': '''autohide autohide-delay autohide-time-modifier tilesize largesize
magnification orientation mineffect minimize-to-application show-recents show-process-indicators
launchanim mru-spaces expose-group-apps expose-animation-duration static-only
wvous-tl-corner wvous-tl-modifier wvous-tr-corner wvous-tr-modifier
wvous-bl-corner wvous-bl-modifier wvous-br-corner wvous-br-modifier'''.split(),
    'com.apple.finder': '''AppleShowAllFiles ShowPathbar ShowStatusBar ShowTabView
FXPreferredViewStyle FXDefaultSearchScope FXEnableExtensionChangeWarning
_FXShowPosixPathInTitle _FXSortFoldersFirst _FXSortFoldersFirstOnDesktop
ShowExternalHardDrivesOnDesktop ShowHardDrivesOnDesktop ShowRemovableMediaOnDesktop
ShowMountedServersOnDesktop NewWindowTarget QuitMenuItem CreateDesktop'''.split(),
    'com.apple.screencapture': ['type', 'disable-shadow', 'show-thumbnail', 'include-date'],
    'com.apple.AppleMultitouchTrackpad': TRACKPAD,
    'com.apple.driver.AppleBluetoothMultitouch.trackpad': TRACKPAD,
    'com.apple.AppleMultitouchMouse': MOUSE,
    'com.apple.driver.AppleBluetoothMultitouch.mouse': MOUSE,
    'com.apple.symbolichotkeys': ['AppleSymbolicHotKeys'],
    'com.apple.spaces': ['spans-displays'],
}
DEFAULT_FILE = Path.home() / '.config/yadm/macos/preferences.plist'
BACKUPS = Path.home() / '.local/state/dotfiles/mac-settings'


def read_domain(domain):
    result = subprocess.run(['/usr/bin/defaults', 'export', domain, '-'], capture_output=True)
    if result.returncode:
        # An absent domain is expected on machines without some input devices.
        # Other errors must not turn into destructive "unset" records.
        message = result.stderr.decode(errors='replace').lower()
        if "does not exist" in message or "domain not found" in message:
            return {}
        raise RuntimeError('Could not read preference domain: ' + domain)
    data = plistlib.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError('Invalid preference domain: ' + domain)
    return data


def capture():
    records = {}
    for domain, keys in ALLOW.items():
        data = read_domain(domain)
        records[domain] = {'values': {k: data[k] for k in keys if k in data},
                           'unset': [k for k in keys if k not in data]}
    return {'format': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'macos_version': platform.mac_ver()[0], 'domains': records}


def validate(snapshot):
    if snapshot.get('format') != 1 or not isinstance(snapshot.get('domains'), dict):
        raise ValueError('Unsupported snapshot format')
    for domain, record in snapshot['domains'].items():
        if domain not in ALLOW:
            raise ValueError('Unapproved domain: ' + domain)
        values, unset = record['values'], record['unset']
        if not isinstance(values, dict) or not isinstance(unset, list):
            raise ValueError('Invalid preference record')
        keys = set(values) | set(unset)
        if keys - set(ALLOW[domain]) or set(values) & set(unset):
            raise ValueError('Invalid/unapproved keys in ' + domain)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            plistlib.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)  # New file remains mode 0600.


def backup(data):
    path = BACKUPS / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '.plist')
    save(path, data)
    return path


def changes(snapshot):
    result = []
    for domain, record in snapshot['domains'].items():
        current = read_domain(domain)
        for key, value in record['values'].items():
            # Distinguish booleans from numbers despite Python equality.
            if key not in current or plistlib.dumps(current[key]) != plistlib.dumps(value):
                result.append((domain, key, value, False))
        for key in record['unset']:
            if key in current:
                result.append((domain, key, None, True))
    return result


def apply(snapshot, plan=True):
    validate(snapshot)
    pending = changes(snapshot)
    for domain, key, value, remove in pending:
        print(('RESET ' if remove else 'SET   ') + domain + ' / ' + key)
    print(str(len(pending)) + ' preference changes; unrelated keys are preserved.')
    if plan or not pending:
        return
    previous = backup(capture())
    print('Before-restore backup: ' + str(previous), flush=True)
    for domain, key, value, remove in pending:
        if remove:
            command = ['/usr/bin/defaults', 'delete', domain, key]
        else:
            # defaults accepts a property-list value, preserving nested types.
            command = ['/usr/bin/defaults', 'write', domain, key, plistlib.dumps(value).decode()]
        result = subprocess.run(command, capture_output=True)
        if result.returncode:
            raise RuntimeError('Restore stopped at ' + domain + '/' + key +
                               '; earlier changes may have applied. Restore backup with mac-settings restore --file ' + str(previous))
    if changes(snapshot):
        raise RuntimeError('Preferences did not persist as expected. Backup: ' + str(previous))
    print('Saved preferences restored. Log out and back in when convenient to refresh cached settings.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['save', 'plan', 'restore'])
    parser.add_argument('--file', type=Path, default=DEFAULT_FILE)
    args = parser.parse_args(argv)
    if platform.system() != 'Darwin':
        parser.error('mac-settings only runs on macOS')
    if args.action == 'save':
        data = capture()
        if args.file.exists():
            old = plistlib.loads(args.file.read_bytes())
            validate(old)
            print('Previous snapshot preserved: ' + str(backup(old)))
        save(args.file, data)
        count = sum(len(r['values']) for r in data['domains'].values())
        print('Saved ' + str(count) + ' explicitly set preferences to ' + str(args.file))
        print('Also recorded unset keys to preserve use of system defaults. No live preferences changed.')
    else:
        snapshot = plistlib.loads(args.file.read_bytes())
        if args.action == 'restore':
            print('Applying saved settings; close System Settings and affected apps first. No apps will be restarted.')
        apply(snapshot, plan=args.action == 'plan')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, plistlib.InvalidFileException) as exc:
        sys.exit(str(exc))
