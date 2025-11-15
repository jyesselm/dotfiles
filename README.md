# Dotfiles

My personal dotfiles managed with [yadm](https://yadm.io/) (Yet Another Dotfiles Manager).

## 📋 What's Included

This repository contains my configuration files for:

- **Shell**: Zsh configuration with custom aliases, functions, and plugins
- **Git**: Global git configuration
- **Taskwarrior**: Task management configuration
- **Conda/Mamba**: Python environment configuration
- **PyMOL**: Molecular visualization configuration
- **Jupyter**: Notebook configuration

## 🚀 Setup on a New Computer

### Prerequisites

- Git installed on your system
- Terminal access (macOS Terminal, Linux terminal, or Windows WSL)

### Step-by-Step Setup

1. **Install yadm**:
   ```bash
   # macOS (using Homebrew)
   brew install yadm
   
   # Linux (using package manager)
   # Ubuntu/Debian:
   sudo apt-get install yadm
   # Fedora/RHEL:
   sudo dnf install yadm
   # Arch Linux:
   sudo pacman -S yadm
   
   # Or install manually (see https://yadm.io/docs/install)
   ```

2. **Clone this repository**:
   ```bash
   yadm clone https://github.com/jyesselm/dotfiles.git
   ```
   
   This command will:
   - Clone the repository into your home directory
   - Automatically run the bootstrap script (`.yadm/bootstrap`)
   - Set up all your dotfiles

3. **Verify the setup**:
   ```bash
   # Check that files are in place
   ls -la ~ | grep "^\."
   
   # Test your shell configuration
   source ~/.zshrc
   
   # Verify yadm is tracking files
   yadm status
   ```

4. **Restart your terminal** or run:
   ```bash
   exec zsh
   ```

### What Gets Set Up

When you run `yadm clone`, the following happens automatically:

- ✅ All dotfiles are copied to your home directory
- ✅ The bootstrap script (`.yadm/bootstrap`) runs automatically
- ✅ Necessary directories are created
- ✅ Dependencies are installed (if configured in bootstrap)
- ✅ Your shell configuration is ready to use

### Manual Setup (Alternative)

If you prefer to set up manually or the bootstrap script didn't run:

```bash
# Clone the repository
yadm clone https://github.com/jyesselm/dotfiles.git

# Manually checkout all files
yadm checkout

# Run bootstrap script manually (if needed)
~/.yadm/bootstrap
```

### Syncing Updates from Another Computer

If you've made changes on another computer and want to sync them:

```bash
# Pull the latest changes
yadm pull

# The files will be updated automatically
# Restart your terminal or source your config:
source ~/.zshrc
```

### Troubleshooting

**Problem**: Bootstrap script didn't run
```bash
# Run it manually
~/.yadm/bootstrap
```

**Problem**: Files not showing up
```bash
# Force checkout all files
yadm checkout --force
```

**Problem**: Conflicts with existing files
```bash
# Backup existing files first, then checkout
yadm clone https://github.com/jyesselm/dotfiles.git
# yadm will warn you about existing files - choose to backup or overwrite
```

## 📁 Structure

```
.
├── .zshrc              # Main zsh configuration
├── .zsh/               # Zsh configuration modules
│   ├── aliases.zsh     # Custom aliases
│   ├── functions.zsh   # Custom functions
│   ├── paths.zsh       # PATH configuration
│   ├── plugins.zsh     # Plugin configuration
│   └── env.zsh         # Environment variables
├── .gitconfig          # Git configuration
├── .taskrc             # Taskwarrior configuration
├── .condarc             # Conda configuration
├── .pymolrc             # PyMOL configuration
├── .config/             # Application configurations
└── .yadm/               # yadm-specific files
    ├── bootstrap        # Setup script for new machines
    └── encrypt          # Files to encrypt (if using encryption)
```

## 🔧 Management

### Adding New Dotfiles

```bash
yadm add ~/.newfile
yadm commit -m "Add new configuration file"
yadm push
```

### Updating Existing Files

```bash
# Edit your files normally, then:
yadm add ~/.zshrc
yadm commit -m "Update zsh configuration"
yadm push
```

### Machine-Specific Configurations

yadm supports alternate files for different machines. Create files with the pattern:
- `.zshrc##machine1` - for machine1
- `.zshrc##machine2` - for machine2

yadm will automatically use the correct file based on the hostname.

## 🔐 Encryption

Sensitive files can be encrypted using yadm's encryption feature. See `.yadm/encrypt` for configuration.

## 📚 Resources

- [yadm Documentation](https://yadm.io/docs/)
- [yadm GitHub](https://github.com/TheLocehiliosan/yadm)

## 📝 License

These dotfiles are provided as-is for personal use. Feel free to use them as inspiration for your own setup!

