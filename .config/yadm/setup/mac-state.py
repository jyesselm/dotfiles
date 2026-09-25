#!/usr/bin/env python3
"""Encrypted current-state backup of Alfred, Bartender and installed-app inventory."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import plistlib
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

BASE = Path.home() / '.local/state/dotfiles/mac-state'
DOMAINS = ['com.runningwithcrayons.Alfred', 'com.runningwithcrayons.Alfred-Preferences',
           'com.surteesstudios.Bartender']


def private_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)


def app_inventory(roots=None):
    roots = roots or [Path('/Applications'), Path.home()/'Applications', Path('/System/Applications')]
    apps, errors = [], []
    for base in roots:
        if not base.exists():
            continue
        for current, dirs, files in os.walk(base, followlinks=False):
            for name in list(dirs):
                if not name.endswith('.app'):
                    continue
                dirs.remove(name)  # Do not count helpers embedded inside apps.
                app = Path(current)/name
                try:
                    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
                    apps.append({'name': name[:-4], 'bundle_id': info.get('CFBundleIdentifier',''),
                                 'version': str(info.get('CFBundleShortVersionString','')),
                                 'build': str(info.get('CFBundleVersion','')), 'path': str(app)})
                except (OSError, ValueError, plistlib.InvalidFileException):
                    apps.append({'name':name[:-4], 'path':str(app), 'version':'unknown'})
                    errors.append('Could not read app metadata: ' + str(app))
    return sorted(apps,key=lambda a:(a['name'].lower(),a['path'])), errors


def inventory():
    apps, errors = app_inventory()
    data = {'created_utc': datetime.now(timezone.utc).isoformat(),
            'macos': platform.mac_ver()[0], 'architecture': platform.machine(),
            'applications': apps, 'errors': errors, 'homebrew': {}}
    brew = shutil.which('brew') or ('/opt/homebrew/bin/brew' if Path('/opt/homebrew/bin/brew').exists() else None)
    if brew:
        for kind in ['formula','cask']:
            result = subprocess.run([brew,'list','--'+kind,'--versions'],capture_output=True,text=True,
                                    env=dict(os.environ,HOMEBREW_NO_AUTO_UPDATE='1'), timeout=90)
            if result.returncode:
                raise RuntimeError('Could not inventory Homebrew ' + kind + ' packages')
            data['homebrew'][kind] = result.stdout.splitlines()
    return data


def public_inventory(state):
    result = {key: state[key] for key in ['created_utc', 'macos', 'architecture', 'homebrew']}
    result['applications'] = [{**{k:v for k,v in app.items() if k != 'path'},
                               'scope': 'system' if app['path'].startswith('/System/') else 'user-installed'}
                              for app in state['applications']]
    return result


def preference_bytes(domain):
    r = subprocess.run(['/usr/bin/defaults','export',domain,'-'],capture_output=True,check=True)
    plistlib.loads(r.stdout)
    return r.stdout


def collect_sources(home):
    support = home/'Library/Application Support/Alfred'
    prefs = support/'prefs.json'
    if not prefs.is_file():
        raise RuntimeError('Alfred prefs.json missing; cannot determine active preferences.')
    current = json.loads(prefs.read_text()).get('current')
    if not current:
        raise RuntimeError('Alfred active preferences path is missing.')
    active = Path(os.path.expanduser(current))
    if not active.is_dir():
        raise RuntimeError('Alfred active preferences are not available locally.')
    sources = [(active,'alfred/active/Alfred.alfredpreferences'),(prefs,'alfred/prefs.json')]
    local = support/'Alfred.alfredpreferences'
    if local.is_dir() and local.resolve() != active.resolve():
        sources.append((local,'alfred/local/Alfred.alfredpreferences'))
    licenses = sorted(support.glob('powerpack.*.dat'))
    sources += [(p,'alfred/activation/'+p.name) for p in licenses]
    bartender = home/'Library/Application Support/Bartender'
    if bartender.exists():
        sources.append((bartender,'bartender/Application Support'))
    for rel in ['.config/karabiner/karabiner.json','.config/yadm/macos/preferences.plist']:
        p=home/rel
        if p.is_file(): sources.append((p,'dotfiles/'+rel))
    return sources, active, len(licenses)


def add_tree(archive, source, name, hashes):
    if source.is_symlink():
        raise RuntimeError('Symlink requires review before backing up: ' + str(source))
    if source.is_dir():
        for p in sorted(source.iterdir()):
            add_tree(archive,p,name+'/'+p.name,hashes)
    elif source.is_file():
        before=source.stat()
        content=source.read_bytes()
        after=source.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise RuntimeError('Configuration changed during backup; rerun: '+str(source))
        entry=tarfile.TarInfo(name); entry.size=len(content)
        entry.mode=0o700 if before.st_mode & 0o111 else 0o600
        archive.addfile(entry,io.BytesIO(content))
        hashes[name]=hashlib.sha256(content).hexdigest()
    else:
        raise RuntimeError('Unsupported backup file: '+str(source))


def add_bytes(archive, name, content, hashes):
    entry=tarfile.TarInfo(name); entry.size=len(content); entry.mode=0o600
    archive.addfile(entry,io.BytesIO(content))
    hashes[name]=hashlib.sha256(content).hexdigest()


def verify_tar(path):
    with tarfile.open(path,'r:gz') as archive:
        names=archive.getnames()
        if len(names)!=len(set(names)):
            raise ValueError('Duplicate backup entries')
        for entry in archive.getmembers():
            if not entry.isfile() or entry.name.startswith('/') or '..' in Path(entry.name).parts:
                raise ValueError('Unsafe archive entry')
        manifest=json.load(archive.extractfile('manifest.json'))
        if set(names)!=set(manifest['sha256'])|{'manifest.json'}:
            raise ValueError('Manifest/file mismatch')
        for name,expected in manifest['sha256'].items():
            actual=hashlib.sha256(archive.extractfile(name).read()).hexdigest()
            if actual!=expected: raise ValueError('Backup checksum mismatch: '+name)
    return manifest


def gpg_command(gpg, home, *args):
    return [gpg,'--homedir',str(home),'--batch','--yes','--no-symkey-cache',
            '--pinentry-mode','loopback','--passphrase-fd','0',*map(str,args)]


def save(destination=None):
    gpg=shutil.which('gpg') or '/opt/homebrew/bin/gpg'
    if not Path(gpg).is_file(): raise RuntimeError('GnuPG is needed: brew install gnupg')
    sources, active, license_count=collect_sources(Path.home())
    state=inventory()
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    folder=BASE/stamp; folder.mkdir(parents=True,mode=0o700)
    key=secrets.token_urlsafe(48).encode()
    recovery=folder/'RECOVERY-KEY.txt'
    private_write(recovery,key+b'\n')
    encrypted=folder/'mac-state.tar.gz.gpg'
    with tempfile.TemporaryDirectory(prefix='.capture-',dir=folder) as temp, tempfile.TemporaryDirectory(prefix='mac-gpg-',dir='/private/tmp') as gpgdir:
        temp=Path(temp); gnupg=Path(gpgdir)
        plain=temp/'snapshot.tar.gz'
        hashes={}
        with tarfile.open(plain,'w:gz') as archive:
            for source,name in sources: add_tree(archive,source,name,hashes)
            for domain in DOMAINS:
                add_bytes(archive,'preferences/'+domain+'.plist',preference_bytes(domain),hashes)
            add_bytes(archive,'inventory.json',json.dumps(state,indent=2).encode(),hashes)
            add_bytes(archive,'RESTORE.md',Path(__file__).with_name('mac-state-restore.md').read_bytes(),hashes)
            manifest={'format':1,'created_utc':state['created_utc'],'sha256':dict(hashes),
                      'alfred_active_source':str(active),'alfred_activation_files':license_count,
                      'application_count':len(state['applications'])}
            add_bytes(archive,'manifest.json',json.dumps(manifest,indent=2).encode(),{})
        plain.chmod(0o600); verify_tar(plain)
        subprocess.run(gpg_command(gpg,gnupg,'--cipher-algo','AES256','--output',encrypted,'--symmetric',plain),
                       input=key+b'\n',capture_output=True,check=True)
        encrypted.chmod(0o600)
        check=temp/'verified.tar.gz'
        subprocess.run(gpg_command(gpg,gnupg,'--output',check,'--decrypt',encrypted),
                       input=key+b'\n',capture_output=True,check=True)
        verify_tar(check)
        if hashlib.sha256(check.read_bytes()).digest()!=hashlib.sha256(plain.read_bytes()).digest():
            raise RuntimeError('Encrypted round-trip mismatch')
    # Inventory contains no license values or configuration payloads; still kept private by default.
    private_write(folder/'inventory.json',json.dumps(state,indent=2).encode())
    checksum=hashlib.sha256(encrypted.read_bytes()).hexdigest()
    private_write(folder/'SHA256.txt',(checksum+'  '+encrypted.name+'\n').encode())
    if destination:
        destination=destination.expanduser()/stamp
        destination.mkdir(parents=True,exist_ok=False,mode=0o700)
        shutil.copy2(encrypted,destination/encrypted.name)
        shutil.copy2(folder/'SHA256.txt',destination/'SHA256.txt')
        if hashlib.sha256((destination/encrypted.name).read_bytes()).hexdigest()!=checksum:
            raise RuntimeError('Copied archive checksum mismatch')
        print('Encrypted copy: '+str(destination/encrypted.name))
    print('Verified encrypted backup: '+str(encrypted))
    print('Recovery key (never uploaded): '+str(recovery))
    print('Store that key in your password manager before relying on this backup on another computer.')
    print(str(len(state['applications']))+' app bundles; '+str(len(hashes))+' verified files; '+str(license_count)+' Alfred activation files.')
    print('Inventory: '+str(folder/'inventory.json'))
    tracked = Path.home()/'.config/yadm/macos/applications.json'
    tracked.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=tracked.parent,delete=False) as stream:
        stage=Path(stream.name)
        stream.write((json.dumps(public_inventory(state),indent=2)+'\n').encode())
    stage.replace(tracked)
    print('Yadm app inventory refreshed: '+str(tracked))
    return folder


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['save'])
    p.add_argument('--destination',type=Path,help='Copy encrypted archive to this folder; never copies recovery key')
    args=p.parse_args()
    if platform.system()!='Darwin': p.error('mac-state runs on macOS only')
    save(args.destination)

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        # Avoid printing process stderr or command data containing private values.
        sys.exit('Backup failed: '+(str(exc) if not isinstance(exc,subprocess.SubprocessError) else 'external command failed; no verified success reported'))
