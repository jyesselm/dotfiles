#!/usr/bin/env python3
"""Terminal-first, repeatable dotfiles setup. --plan and --doctor never install."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

import layout as lay

HERE = Path(__file__).resolve().parent
MICROMAMBA = {
    'x86_64': ('linux-64', '366cd9cd8be14df1ab8ed50352a82111082a36686b2d389fdb79a92c3fafb3e3'),
    'aarch64': ('linux-aarch64', '9f93b974adcb4d166996af969b6cd371287d1a3e52733704727884d9b74cb7a7'),
}
TOOLS = ['git', 'tmux', 'nvim', 'yazi', 'ya', 'fzf', 'fd', 'rg', 'zoxide',
         'starship', 'atuin', 'bat', 'jq', 'uv', 'gh', 'lazygit', 'node', 'zsh']
MINIMUM = {'tmux': (3, 6), 'nvim': (0, 11), 'yazi': (26, 9, 1), 'fzf': (0, 53)}


def detect_profile():
    if platform.system() == 'Darwin':
        return 'mac'
    if platform.system() == 'Linux':
        return 'cluster' if Path('/util/opt').is_dir() or 'swan' in platform.node() else 'linux'
    raise RuntimeError('Supported systems: macOS and Linux (including WSL).')


def version(text):
    match = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', text)
    if not match:
        return ()
    return tuple(int(v or 0) for v in match.groups())


def live_differs(config, destination) -> bool:
    """True for a regular (non-symlink) live file whose content differs from the tracked one."""
    return destination.exists() and not destination.is_symlink() and destination.read_bytes() != config.read_bytes()


class Setup:
    def __init__(self, args, root=None, assets=HERE):
        self.args = args
        self.root = Path(root) if root is not None else Path.home()
        self.assets = Path(assets)
        self.profile = detect_profile() if args.profile == 'auto' else args.profile
        self.base = self.root / '.local/share/dotfiles'
        self.shims = self.base / 'bin'
        self.envdir = self.base / 'tools'
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
        extra = [str(self.shims), str(self.root / '.local/bin'), '/opt/homebrew/bin', '/usr/local/bin']
        self.env['PATH'] = os.pathsep.join(extra + [self.env.get('PATH', '')])
        self.errors = []
        self._class = None

    def say(self, text):
        print(text, flush=True)

    def find(self, name):
        return shutil.which(name, path=self.env['PATH'])

    def run(self, argv, **kwargs):
        self.say('  $ ' + shlex.join(list(map(str, argv))))
        if self.args.plan:
            return
        options = {'env': self.env, **kwargs}
        if 'timeout' in options:
            self.run_timed(list(map(str, argv)), options)
        else:
            subprocess.run(list(map(str, argv)), check=True, **options)

    def run_timed(self, argv, options):
        """Run in its own session; on timeout kill the whole process group (yadm->git, brew->ruby)."""
        timeout = options.pop('timeout')
        with subprocess.Popen(argv, start_new_session=True, **options) as proc:
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
                raise
        if code:
            raise subprocess.CalledProcessError(code, argv)

    def read(self, argv, cwd=None, timeout_s=60):
        """Run a read-only command (even in plan mode); never raises for missing binary or timeout."""
        argv = list(map(str, argv))
        try:
            return subprocess.run(argv, capture_output=True, text=True, check=False, env=self.env, cwd=cwd, timeout=timeout_s)
        except FileNotFoundError as exc:
            return subprocess.CompletedProcess(argv, 127, '', str(exc))
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(argv, 124, '', 'timed out after %ss' % timeout_s)

    def read_ok(self, argv, what, **kwargs) -> str:
        """stdout of a read-only command; RuntimeError(what + ': ' + stderr) when it fails."""
        result = self.read(argv, **kwargs)
        if result.returncode:
            raise RuntimeError(what + ': ' + result.stderr.strip()[:200])
        return result.stdout

    def phase(self, name, action):
        self.say('\n' + name)
        try:
            return action()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            self.errors.append(name + ': ' + str(exc))
            self.say('  FAILED: ' + str(exc))
            return None

    def machine_class(self) -> str:
        """yadm's local.class (laptop|studio|linux|cluster), falling back to the profile."""
        if self._class is None:
            yadm = self.find('yadm')
            out = self.read([yadm, 'config', 'local.class']).stdout.strip() if yadm else ''
            self._class = out.splitlines()[0].strip() if out else self.profile
        return self._class

    def layout(self) -> lay.LayoutReport:
        """Create missing manifest directories; report expected-but-absent and unplanned entries."""
        text = (self.assets / 'layout.txt').read_text()
        report = lay.LayoutReport()
        for entry in lay.missing_dirs(self.root, lay.parse_layout(text, self.profile, self.machine_class())):
            if not entry.create:
                report.expected.append(entry.path)
                self.say('  Expected, not created: ~/' + entry.path + ' (created by another program)')
                continue
            self.say('  Create ~/' + entry.path)
            if not self.args.plan:
                (self.root / entry.path).mkdir(parents=True, exist_ok=True)
                report.created.append(entry.path)
        report.unplanned = lay.unplanned_entries(self.root, lay.parse_layout(text, None, None))
        for name in report.unplanned:
            self.say('  Unplanned: ' + name)
        return report

    def portability(self) -> list:
        """Failures for literal home paths in yadm-tracked files."""
        yadm = self.find('yadm')
        listing = self.read([yadm, 'ls-files', '-z'], cwd=self.root) if yadm else None
        if listing is None or listing.returncode:
            self.say('  Portability check skipped: yadm file list unavailable.')
            return []
        hits, known = lay.find_home_paths(self.root, listing.stdout)
        if known:
            self.say('  Known per-machine absolute paths: ' + str(len({k.rsplit(':', 1)[0] for k in known})) + ' files (iTerm prefs, launchd plist)')
        return ['Absolute home path: ' + hit for hit in hits]

    def clone(self, url, destination, revision=None, sentinel=None, private=False):
        destination = Path(destination)
        if destination.exists():
            if not (destination / '.git').exists() or (sentinel and not (destination / sentinel).exists()):
                raise RuntimeError('Existing incomplete/non-Git installation left untouched: ' + str(destination))
            self.say('  Keep existing checkout: ' + str(destination))
            return
        if self.args.plan:
            self.say('  Clone ' + url + ' -> ' + str(destination) + (' at ' + revision if revision else ' (default branch)'))
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.dotfiles-clone-', dir=destination.parent) as stage:
            checkout = Path(stage) / 'repo'
            self.run(['gh', 'repo', 'clone', url, checkout] if private else ['git', 'clone', url, checkout])
            if revision:
                self.run(['git', '-C', checkout, 'checkout', '--detach', revision])
            if sentinel and not (checkout / sentinel).exists():
                raise RuntimeError('Required file missing from ' + url + ': ' + sentinel)
            checkout.rename(destination)

    def packages(self):
        if self.args.skip_packages:
            self.say('  Package installation skipped by request.')
            return
        if self.profile == 'mac':
            brew = self.find('brew') or 'brew'
            if not self.find('brew') and not self.args.plan:
                raise RuntimeError('Install Homebrew from https://brew.sh, then rerun. Bootstrap does not pipe remote installers into a shell.')
            manifests = ['Brewfile']
            if self.args.previews:
                manifests.append('Brewfile.previews')
            if self.args.desktop:
                manifests.append('Brewfile.desktop')
            for name in manifests:
                self.run([brew, 'bundle', 'install', '--no-upgrade', '--file', self.assets / name])
            return
        self.linux_tools()

    def linux_tools(self):
        specs = [s.strip() for s in (self.assets / 'linux-packages.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
        if self.args.previews:
            specs += ['7zip', 'resvg', 'poppler', 'ffmpeg']
        digest = hashlib.sha256('\n'.join(specs).encode()).hexdigest()
        marker = self.envdir / '.dotfiles-manifest'
        if self.args.plan:
            self.say('  Install checksum-verified Micromamba 2.9.0-0 in ' + str(self.base))
            self.say('  Create/update isolated environment ' + str(self.envdir))
            self.say('  Packages: ' + ', '.join(specs))
            self.say('  Expose terminal commands through ' + str(self.shims) + '; leave Python/research environments alone.')
            return
        unchanged = marker.exists() and marker.read_text().strip() == digest
        if not unchanged or not all((self.envdir / 'bin' / name).exists() for name in TOOLS):
            arch = platform.machine()
            if arch not in MICROMAMBA:
                raise RuntimeError('No verified Micromamba binary configured for ' + arch)
            tag, checksum = MICROMAMBA[arch]
            self.base.mkdir(parents=True, exist_ok=True)
            binary = self.base / 'micromamba'
            if not binary.exists() or hashlib.sha256(binary.read_bytes()).hexdigest() != checksum:
                url = 'https://github.com/mamba-org/micromamba-releases/releases/download/2.9.0-0/micromamba-' + tag
                self.say('  Download and verify ' + url)
                with urllib.request.urlopen(url, timeout=90) as response:
                    data = response.read()
                if hashlib.sha256(data).hexdigest() != checksum:
                    raise RuntimeError('Micromamba checksum mismatch; nothing installed.')
                temporary = binary.with_suffix('.tmp-' + uuid.uuid4().hex)
                temporary.write_bytes(data)
                temporary.chmod(0o755)
                temporary.replace(binary)
            verb = 'install' if (self.envdir / 'conda-meta').is_dir() else 'create'
            self.run([binary, verb, '-y', '-r', self.base / 'mamba', '-p', self.envdir,
                      '--override-channels', '-c', 'conda-forge', '--strict-channel-priority', *specs])
            marker.write_text(digest + '\n')
        else:
            self.say('  Tool environment already matches this manifest.')
        self.shims.mkdir(parents=True, exist_ok=True)
        for name in TOOLS + ['7z', '7zz', 'resvg', 'pdftoppm', 'pdftotext', 'ffmpeg', 'ffprobe']:
            executable = self.envdir / 'bin' / name
            if executable.exists():
                wrapper = self.shims / name
                text = '#!/bin/sh\n# Managed by dotfiles-setup\nexec ' + shlex.quote(str(executable)) + ' "$@"\n'
                if wrapper.exists() and '# Managed by dotfiles-setup' not in wrapper.read_text():
                    raise RuntimeError('Unmanaged command left untouched: ' + str(wrapper))
                wrapper.write_text(text)
                wrapper.chmod(0o755)

    def shell(self):
        for row in (self.assets / 'shell-plugins.lock').read_text().splitlines():
            if row.strip() and not row.startswith('#'):
                relative, url, revision, sentinel = row.split()
                self.clone(url, self.root / relative, revision, sentinel)
        if not self.args.plan:
            (self.root / '.cache/zsh').mkdir(parents=True, exist_ok=True)

    def link(self, source, destination):
        if destination.is_symlink() and destination.resolve() == source.resolve():
            self.say('  Already linked: ' + str(destination))
            return
        self.say('  Link ' + str(destination) + ' -> ' + str(source))
        if self.args.plan:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            backup = destination.with_name(destination.name + '.backup-' + uuid.uuid4().hex[:12])
            destination.rename(backup)
            self.say('  Preserved previous settings: ' + str(backup))
        destination.symlink_to(source)

    def editors(self, protect_live=False) -> list:
        """Link tracked Cursor settings; with protect_live, keep differing live files and return them."""
        parent = self.root / ('Library/Application Support' if self.profile == 'mac' else '.config')
        held = []
        user = parent / 'Cursor/User'
        installed = user.exists() or Path('/Applications/Cursor.app').exists() or (self.root / 'Applications/Cursor.app').exists()
        for target in ('settings.json', 'keybindings.json'):
            config = self.root / '.config/yadm/files' / ('cursor-' + target)
            if not config.exists() or not (installed or self.args.desktop):
                continue
            if protect_live and live_differs(config, user / target):
                held.append(str(user / target))
                self.say('  Kept live file (differs from tracked): ' + str(user / target))
                continue
            self.link(config, user / target)
        return held

    def tmux(self):
        self.run(['sh', self.root / '.config/tmux/setup.sh'])

    def neovim(self):
        if self.args.skip_nvim:
            self.say('  Neovim plugin setup skipped by request.')
            return
        # Restore the committed lockfile instead of silently upgrading all plugins.
        verify = "+lua for _,name in ipairs({'flash','which-key','snacks','lspconfig'}) do if not pcall(require,name) then vim.cmd('cquit 1') end end"
        self.run(['nvim', '--headless', '-i', 'NONE', '+Lazy! restore', verify, '+qa'])

    def games(self):
        self.run(['gh', 'auth', 'status'])
        for name in ['tmux-dojo', 'nvim-dojo']:
            destination = self.base / 'repos' / name
            self.clone('https://github.com/jyesselm/' + name + '.git', destination, sentinel='install.sh', private=True)
            command = ['sh', destination / 'install.sh']
            if name == 'nvim-dojo':
                command.append('--lazy')
            self.run(command)

    def search(self):
        destination = self.base / 'repos/search-cli'
        self.clone('https://github.com/jyesselm/search-cli.git', destination, sentinel='pyproject.toml')
        self.run(['uv', 'tool', 'install', '--python', '3.12', '--editable', destination])

    def doctor(self):
        self.say('\nDoctor (read-only checks)')
        failures = []
        for name in TOOLS:
            executable = self.find(name)
            if not executable:
                failures.append(name + ' missing')
                self.say('  MISSING ' + name)
                continue
            minimum = MINIMUM.get(name)
            if minimum:
                args = [executable, '-V' if name == 'tmux' else '--version']
                try:
                    out = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=8, check=True).stdout
                    if version(out) < minimum:
                        failures.append(name + ' needs ' + '.'.join(map(str, minimum)) + '+')
                        self.say('  OLD ' + name + ': ' + out.splitlines()[0])
                        continue
                except (OSError, subprocess.SubprocessError) as exc:
                    failures.append(name + ' version check failed: ' + str(exc))
                    continue
            self.say('  OK ' + name + ' -> ' + executable)
        for relative in ['.config/yazi/yazi.toml', '.config/yazi/theme.toml', '.config/yazi/keymap.toml',
                         '.oh-my-zsh/oh-my-zsh.sh', '.tmux/plugins/tpm/tpm', '.config/nvim/init.lua']:
            if not (self.root / relative).is_file():
                failures.append('Missing ' + relative)
        failures += self.portability()
        if self.args.games:
            for relative in ['.local/bin/tmux-dojo', '.config/nvim/lua/plugins/nvim-dojo.lua']:
                if not (self.root / relative).is_file():
                    failures.append('Missing optional game: ' + relative)
        if self.args.search and not self.find('s'):
            failures.append('search-cli command s missing')
        if self.args.previews:
            for name in ['resvg', 'pdftoppm', 'ffmpeg', 'ffprobe']:
                if not self.find(name):
                    failures.append('Missing preview tool: ' + name)
            if not (self.find('7z') or self.find('7zz')):
                failures.append('Missing archive preview tool: 7z or 7zz')
        self.say('  Manual: select JetBrainsMono Nerd Font in your terminal; fonts belong on the client for SSH.')
        self.say('  Accounts: gh auth login / atuin login as needed; bootstrap does not copy credentials.')
        if self.profile == 'mac':
            self.say('  Mac preferences: mac-settings plan previews saved settings; mac-settings restore explicitly applies them with a backup.')
        self.say('  Existing tmux servers keep their old version/config. On Swan use tmux-modern after detaching.')
        for failure in failures:
            self.say('  NEEDS ATTENTION: ' + failure)
        return failures

    def execute(self):
        self.say(('PLAN ONLY' if self.args.plan else 'DOTFILES SETUP') + ' — ' + self.profile)
        if self.args.desktop and self.profile != 'mac':
            raise RuntimeError('--desktop currently supports macOS only; Linux desktop apps are left to your distribution.')
        if self.args.doctor:
            return int(bool(self.doctor()))
        self.phase('Directory layout', self.layout)
        self.phase('Terminal packages', self.packages)
        self.phase('Shell and shell plugins', self.shell)
        self.phase('Editor settings for installed apps', self.editors)
        self.phase('Tmux plugins and menu', self.tmux)
        self.phase('Neovim plugins from lockfile', self.neovim)
        if self.args.games:
            self.phase('Private practice games (requires GitHub authentication)', self.games)
        if self.args.search:
            self.phase('Search CLI', self.search)
        if not self.args.plan:
            self.errors += self.doctor()
        if self.errors:
            self.say('\nSetup incomplete; rerun after resolving:')
            for error in self.errors:
                self.say('  - ' + error)
            return 1
        self.say('\nPlan complete. No files changed.' if self.args.plan else '\nSetup complete. Open a new terminal to load the environment.')
        return 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--plan', action='store_true', help='Show actions without writing files, downloads or installs')
    mode.add_argument('--doctor', action='store_true', help='Read-only tool/version/config checks')
    action = p.add_mutually_exclusive_group()
    action.add_argument('--sync', action='store_true', help='Converge this machine; combine with --plan')
    action.add_argument('--status', action='store_true', help='Show the last sync result')
    action.add_argument('--install-schedule', action='store_true', help='Install the daily launchd job / crontab line')
    action.add_argument('--fleet', action='store_true', help='Last sync of every machine in setup/fleet.txt, over ssh')
    p.add_argument('--profile', choices=['auto', 'mac', 'linux', 'cluster'], default='auto')
    for name, help_text in [('desktop','Also install iTerm2 and Cursor (Mac)'),
                            ('previews','Install PDF, SVG, archive and video preview tools'),
                            ('games','Install the two private Dojo repositories'),
                            ('search','Install search-cli from its default GitHub branch'),
                            ('skip-packages','Configure only; do not install terminal packages'),
                            ('skip-nvim','Skip Neovim plugin restore')]:
        p.add_argument('--' + name, action='store_true', help=help_text)
    return p


def dispatch(args) -> int:
    """Run the requested action; sync modules are imported lazily."""
    setup = Setup(args)
    if args.status or args.fleet:
        from sync import fleet, print_status
        from sync_schedule import is_installed
        if args.fleet:
            return fleet(setup, is_installed(setup), setup.assets / 'fleet.txt')
        return print_status(setup.root, is_installed(setup))
    if args.install_schedule:
        from sync_schedule import install
        return install(setup)
    if args.sync:
        from sync import Sync
        return Sync(setup).execute()
    return setup.execute()


def main(argv=None) -> int:
    if sys.version_info < (3, 9):
        sys.exit('dotfiles-setup requires Python 3.9 or newer.')
    p = parser()
    args = p.parse_args(argv)
    if args.doctor and (args.sync or args.status or args.install_schedule or args.fleet):
        p.error('--doctor cannot be combined with --sync, --status, --fleet or --install-schedule')
    try:
        return dispatch(args)
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))


if __name__ == '__main__':
    sys.exit(main())
