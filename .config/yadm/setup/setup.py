#!/usr/bin/env python3
"""converge: make this computer match the dotfiles repo. `setup` bootstraps, `sync` converges daily; --plan and doctor never install."""
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
DEVELOPING = 'local/code/python/developing'  # grc-managed checkouts
# command -> (repo it runs from, pip extras); a commit on main propagates via sync. `s` needs gui for `s gui` and docs for previews.
CHECKOUT_TOOLS = {'grc': ('git-repo-checker', ''), 's': ('search-cli', '[gui,docs]')}


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

    def read(self, argv, cwd=None, timeout_s=60, input=None):
        """Run a read-only command (even in plan mode); never raises for missing binary or timeout."""
        argv = list(map(str, argv))
        try:
            return subprocess.run(argv, capture_output=True, text=True, check=False, env=self.env, cwd=cwd, timeout=timeout_s, input=input)
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
        """Create missing manifest directories and links; report expected-but-absent and unplanned entries."""
        text = (self.assets / 'layout.txt').read_text()
        report = lay.LayoutReport()
        for entry in lay.missing_dirs(self.root, lay.parse_layout(text, self.profile, self.machine_class())):
            target = self.root / entry.link if entry.link else None
            if not entry.create:
                report.expected.append(entry.path)
                self.say('  Expected, not created: ~/' + entry.path + ' (created by another program)')
                continue
            if target is not None and not target.is_dir():
                report.expected.append(entry.path)
                self.say('  Expected, not linked: ~/%s -> ~/%s (target absent)' % (entry.path, entry.link))
                continue
            self.say('  Create ~/' + entry.path + (' -> ~/' + entry.link if entry.link else ''))
            if not self.args.plan:
                path = self.root / entry.path
                if target is None:
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if path.is_symlink():  # dangling link to a target that is gone
                        path.unlink()
                    path.symlink_to(target)
                report.created.append(entry.path)
        report.unplanned = lay.unplanned_entries(self.root, lay.parse_layout(text, None, None))
        for name in report.unplanned:
            self.say('  Unplanned: ' + name)
        return report

    def shell_path(self) -> list:
        """Failures when an interactive login zsh resolves grc (and s) elsewhere than the uv installs in ~/.local/bin."""
        zsh = self.find('zsh')
        if not zsh:
            return []
        names = ['grc'] + (['s'] if self.args.search else [])
        script = 'for n in %s; do print -r -- "$n=$(whence -p $n)"; done' % ' '.join(names)
        probe = self.read([zsh, '-ilc', script], timeout_s=30)
        if probe.returncode:
            return ['shell PATH check failed: zsh -ilc exited %d' % probe.returncode]
        expected = (self.root / '.local/bin').resolve()
        failures = []
        for line in probe.stdout.splitlines():
            name, _, found = line.partition('=')
            if not found or Path(found).parent.resolve() != expected:
                failures.append('%s resolves to %s in a login shell, not ~/.local/bin/%s (uv install): check PATH order in ~/.zsh/tools.zsh'
                                % (name, found or 'nothing', name))
        return failures

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

    def checkout(self, command) -> Path:
        return self.root / DEVELOPING / CHECKOUT_TOOLS[command][0]

    def extras(self, command) -> str:
        return CHECKOUT_TOOLS[command][1]

    def tool(self, command):
        """Install `command` editable from its developing checkout (cloned if absent); sync fast-forwards it, so a commit on main reaches every machine."""
        checkout = self.checkout(command)
        self.clone('https://github.com/jyesselm/' + checkout.name + '.git', checkout, sentinel='pyproject.toml')
        self.run(['uv', 'tool', 'install', '--python', '3.12', '--editable', str(checkout) + self.extras(command)])

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
        if not self.find('grc'):
            failures.append('grc missing; converge sync cannot sync repos')
        if self.args.search and not self.find('s'):
            failures.append('search-cli command s missing')
        failures += self.shell_path()
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
        if self.args.command == 'doctor':
            return int(bool(self.doctor()))
        self.phase('Directory layout', self.layout)
        self.phase('Terminal packages', self.packages)
        self.phase('Shell and shell plugins', self.shell)
        self.phase('Editor settings for installed apps', self.editors)
        self.phase('Tmux plugins and menu', self.tmux)
        self.phase('Neovim plugins from lockfile', self.neovim)
        self.phase('Repo checker (grc) from its developing checkout', lambda: self.tool('grc'))
        if self.args.games:
            self.phase('Private practice games (requires GitHub authentication)', self.games)
        if self.args.search:
            self.phase('Search CLI', lambda: self.tool('s'))
        if not self.args.plan:
            self.errors += self.doctor()
        if self.errors:
            self.say('\nSetup incomplete; rerun after resolving:')
            for error in self.errors:
                self.say('  - ' + error)
            return 1
        self.say('\nPlan complete. No files changed.' if self.args.plan else '\nSetup complete. Open a new terminal to load the environment.')
        return 0


COMMANDS = {  # subcommand -> (help, flag it replaces; `dotfiles-setup --flag` still works through normalize())
    'setup': ('Bootstrap this computer (what yadm bootstrap runs); flags choose optional components', None),
    'sync': ('Converge this computer: layout, dotfiles, packages, repos, apps, defaults, hotkeys, doctor', '--sync'),
    'status': ("Last sync, each warning's details and how to clear it", '--status'),
    'doctor': ('Read-only tool/version/config/PATH checks', '--doctor'),
    'schedule': ('Install the daily launchd job (Mac) or crontab line (Linux)', '--install-schedule'),
    'fleet': ('Last check-in of every machine (fetches the status/* branches)', '--fleet'),
    'checkin': ("Push this machine's last sync result now, then show the fleet", '--checkin'),
    'adopt-extras': ("Mac: allow this computer's current brew extras (appends to setup/extras.txt)", '--adopt-extras'),
}
LEGACY = {flag: name for name, (_, flag) in COMMANDS.items() if flag}
FLAGS = [('plan', 'Show actions without writing files, downloads or installs'),
         ('desktop', 'Also install iTerm2 and Cursor (Mac)'),
         ('previews', 'Install PDF, SVG, archive and video preview tools'),
         ('games', 'Install the two private Dojo repositories'),
         ('search', 'Install search-cli (command s) from its developing checkout'),
         ('skip-packages', 'Configure only; do not install terminal packages'),
         ('skip-nvim', 'Skip Neovim plugin restore')]


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--profile', choices=['auto', 'mac', 'linux', 'cluster'], default='auto')
    for name, help_text in FLAGS:
        common.add_argument('--' + name, action='store_true', help=help_text)
    p = argparse.ArgumentParser(prog='converge', description=__doc__)
    commands = p.add_subparsers(dest='command', metavar='command', required=True)
    for name, (help_text, _) in COMMANDS.items():
        sub = commands.add_parser(name, help=help_text, description=help_text, parents=[common])
        if name == 'status':
            sub.add_argument('--all', action='store_true', help='Every detail line, not just the first 12 per group')
    return p


def normalize(argv) -> list:
    """Accept the old flag form (dotfiles-setup --sync --plan): the action flag becomes the subcommand, none means setup."""
    argv = list(argv)
    if argv and (argv[0] in COMMANDS or argv[0] in ('-h', '--help')):
        return argv
    flags = [a for a in argv if a in LEGACY]
    if len(flags) > 1:
        parser().error('one command at a time, not ' + ' '.join(flags))
    return [LEGACY[flags[0]] if flags else 'setup'] + [a for a in argv if a not in LEGACY]


def parse(argv):
    return parser().parse_args(normalize(argv))


def dispatch(args) -> int:
    """Run the requested command; sync modules are imported lazily."""
    setup = Setup(args)
    if args.command == 'status':
        from sync import print_status
        from sync_schedule import is_installed
        return print_status(setup.root, is_installed(setup), show_all=args.all)
    if args.command in ('fleet', 'checkin'):
        from sync import fleet
        return fleet(setup, setup.assets / 'fleet.txt', checkin=args.command == 'checkin')
    if args.command == 'schedule':
        from sync_schedule import install
        return install(setup)
    if args.command == 'adopt-extras':
        from sync_mac import adopt_extras
        return adopt_extras(setup, setup.machine_class(), Path('/Applications'))
    if args.command == 'sync':
        from sync import Sync
        return Sync(setup).execute()
    return setup.execute()  # setup, doctor


def main(argv=None) -> int:
    if sys.version_info < (3, 9):
        sys.exit('converge requires Python 3.9 or newer.')
    try:
        return dispatch(parse(sys.argv[1:] if argv is None else argv))
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))


if __name__ == '__main__':
    sys.exit(main())
