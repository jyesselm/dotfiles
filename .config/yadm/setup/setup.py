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
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

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

    def say(self, text):
        print(text, flush=True)

    def find(self, name):
        return shutil.which(name, path=self.env['PATH'])

    def run(self, argv, **kwargs):
        self.say('  $ ' + shlex.join(list(map(str, argv))))
        if not self.args.plan:
            subprocess.run(list(map(str, argv)), check=True, env=self.env, **kwargs)

    def phase(self, name, action):
        self.say('\n' + name)
        try:
            action()
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self.errors.append(name + ': ' + str(exc))
            self.say('  FAILED: ' + str(exc))

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

    def editors(self):
        parent = self.root / ('Library/Application Support' if self.profile == 'mac' else '.config')
        for name, app, source in [('Code', 'Visual Studio Code', 'vscode-settings.json'), ('Cursor', 'Cursor', 'cursor-settings.json')]:
            destination = parent / name / 'User/settings.json'
            installed = destination.parent.exists() or Path('/Applications', app + '.app').exists() or (self.root / 'Applications' / (app + '.app')).exists()
            config = self.root / '.config/yadm/files' / source
            if config.exists() and (installed or self.args.desktop):
                self.link(config, destination)

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
    p.add_argument('--profile', choices=['auto', 'mac', 'linux', 'cluster'], default='auto')
    for name, help_text in [('desktop','Also install iTerm2, VS Code, Cursor and Obsidian (Mac)'),
                            ('previews','Install PDF, SVG, archive and video preview tools'),
                            ('games','Install the two private Dojo repositories'),
                            ('search','Install search-cli from its default GitHub branch'),
                            ('skip-packages','Configure only; do not install terminal packages'),
                            ('skip-nvim','Skip Neovim plugin restore')]:
        p.add_argument('--' + name, action='store_true', help=help_text)
    return p


if __name__ == '__main__':
    if sys.version_info < (3,9):
        sys.exit('dotfiles-setup requires Python 3.9 or newer.')
    try:
        sys.exit(Setup(parser().parse_args()).execute())
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))
