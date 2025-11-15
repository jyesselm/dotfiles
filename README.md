# Dotfiles Management with yadm

This repository contains dotfiles managed using [yadm](https://yadm.io/) (Yet Another Dotfiles Manager).

## What is yadm?

yadm is a dotfile management tool that uses Git under the hood. It allows you to:
- Track your dotfiles in a Git repository
- Sync your configuration across multiple machines
- Use Git features like branching, merging, and encryption
- Automatically set up new machines with a bootstrap script

## Quick Start

### On a New Machine

1. **Install yadm** (if not already installed):
   ```bash
   # macOS
   brew install yadm
   
   # Linux (Debian/Ubuntu)
   sudo apt-get install yadm
   
   # Or install manually
   curl -fLo /usr/local/bin/yadm https://github.com/TheLocehiliosan/yadm/raw/master/yadm
   chmod +x /usr/local/bin/yadm
   ```

2. **Clone your dotfiles**:
   ```bash
   yadm clone <your-repo-url>
   ```
   
   This will:
   - Clone your dotfiles repository
   - Automatically run the `.yadm/bootstrap` script to set up your environment
   - Install dependencies and configure your system

3. **Restart your terminal** to apply changes

### On an Existing Machine

If you already have yadm set up, just pull the latest changes:

```bash
yadm pull
```

## Common yadm Commands

### Basic Operations

```bash
# Check status of your dotfiles
yadm status

# Add files to tracking
yadm add ~/.zshrc
yadm add ~/.config/starship.toml

# Commit changes
yadm commit -m "Update zsh configuration"

# Push to remote repository
yadm push

# Pull latest changes
yadm pull

# List all tracked files
yadm ls-files
```

### Managing Files

```bash
# Add a new dotfile
yadm add ~/.gitconfig

# Remove a file from tracking (but keep it locally)
yadm rm --cached ~/.somefile

# See what files have changed
yadm diff

# View commit history
yadm log
```

### Repository Management

```bash
# Initialize a new yadm repository
yadm init

# Add a remote repository
yadm remote add origin <your-repo-url>

# Check remote configuration
yadm remote -v

# Clone on a new machine
yadm clone <your-repo-url>
```

## File Structure

This repository contains:

```
~/
├── .zshrc                    # Main zsh configuration
├── .zsh/                      # Modular zsh configuration
│   ├── aliases.zsh           # Command aliases
│   ├── env.zsh               # Environment variables
│   ├── functions.zsh         # Custom functions
│   ├── paths.zsh             # PATH configuration
│   ├── plugins.zsh           # Plugin configuration
│   └── completion.zsh        # Tab completion settings
├── .config/
│   ├── starship.toml         # Starship prompt configuration
│   └── nvim/                  # Neovim configuration
│       ├── init.lua
│       └── lua/plugins/      # Neovim plugin configs
├── .gitconfig                 # Git configuration
├── .pymolrc                   # PyMOL configuration
└── .yadm/
    └── bootstrap              # Bootstrap script (runs on clone)
```

## Bootstrap Script

The `.yadm/bootstrap` script runs automatically when you:
- Clone your dotfiles: `yadm clone <repo-url>`
- Checkout your dotfiles: `yadm checkout`

It automatically:
- Installs Homebrew (if on macOS)
- Installs essential tools (git, zsh, vim, etc.)
- Sets up zsh as default shell
- Installs Oh My Zsh (if needed)
- Creates necessary directories
- Sets up development environments

You can customize this script to install your specific tools and dependencies.

## Encryption

yadm supports encrypting sensitive files (like SSH keys or API tokens).

### Setting Up Encryption

1. **Create `.yadm/encrypt` file** and list files to encrypt:
   ```bash
   echo ".ssh/id_rsa" >> .yadm/encrypt
   echo ".aws/credentials" >> .yadm/encrypt
   echo ".gnupg/*" >> .yadm/encrypt
   ```

2. **yadm will automatically encrypt** these files when committing

3. **Files are automatically decrypted** when you clone or checkout

### Managing Encrypted Files

```bash
# Add a file to encryption list
echo ".secret_file" >> .yadm/encrypt

# Re-encrypt all files
yadm encrypt

# Decrypt all files
yadm decrypt
```

See [yadm encryption documentation](https://yadm.io/docs/encryption) for more details.

## OS-Specific Configuration

yadm supports OS-specific files using the `##os.OSNAME` suffix:

```bash
# macOS-specific file
.zshrc##os.Darwin

# Linux-specific file
.zshrc##os.Linux

# Both macOS and Linux
.config##os.Darwin
.config##os.Linux
```

When you clone on a specific OS, yadm will automatically use the correct file.

## Best Practices

1. **Don't commit sensitive data**:
   - SSH private keys (use encryption)
   - API tokens (use encryption)
   - Passwords (use encryption or environment variables)

2. **Exclude machine-specific files**:
   - Cache directories (`.cache/`)
   - History files (`.zsh_history`, `.bash_history`)
   - Temporary files
   - Use `.yadm/encrypt` or `.gitignore` to exclude them

3. **Keep bootstrap script updated**:
   - Update `.yadm/bootstrap` as your setup evolves
   - Test it on a fresh machine periodically

4. **Use meaningful commit messages**:
   ```bash
   yadm commit -m "Update zsh aliases"
   yadm commit -m "Add neovim configuration"
   ```

5. **Regular backups**:
   - Push to remote repository regularly
   - Consider multiple remotes for redundancy

## Troubleshooting

### yadm not found
- **macOS**: `brew install yadm`
- **Linux**: See [yadm installation guide](https://yadm.io/docs/install)

### Bootstrap script fails
- Check that you have necessary permissions
- On macOS, you may need to allow Homebrew installation
- On Linux, you may need sudo for package installation

### Files not being tracked
- Check `yadm status` to see what's tracked
- Use `yadm add <file>` to explicitly add files
- Check `.yadm/encrypt` if files should be encrypted

### Legacy paths warning
If you see warnings about legacy paths, run:
```bash
yadm upgrade
```
This will migrate yadm data to the new XDG Base Directory paths.

### Conflicts when pulling
If you have local changes that conflict with remote:
```bash
# See conflicts
yadm status

# Resolve conflicts manually, then
yadm add <resolved-files>
yadm commit -m "Resolve conflicts"
```

## Resources

- [yadm Documentation](https://yadm.io/docs/)
- [yadm GitHub](https://github.com/TheLocehiliosan/yadm)
- [yadm Examples](https://github.com/TheLocehiliosan/yadm/wiki/Example-Configurations)

## License

This dotfiles setup is provided as-is. Feel free to use and modify for your needs.
