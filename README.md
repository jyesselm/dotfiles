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

## 🚀 Quick Start

### On a New Machine

1. **Install yadm**:
   ```bash
   # macOS
   brew install yadm
   
   # Linux (see https://yadm.io/docs/install for other options)
   ```

2. **Clone this repository**:
   ```bash
   yadm clone https://github.com/jyesselm/dotfiles.git
   ```

3. **The bootstrap script will run automatically** to set up your environment.

### Manual Setup

If you prefer to set up manually:

```bash
yadm clone https://github.com/jyesselm/dotfiles.git
yadm checkout
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

