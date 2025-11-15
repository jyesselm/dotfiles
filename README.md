# Dotfiles Management

[![Test Dotfiles Setup](https://github.com/YOUR_USERNAME/dotfiles/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/dotfiles/actions/workflows/test.yml)

This repository contains scripts and configuration for managing dotfiles using [yadm](https://yadm.io/) (Yet Another Dotfiles Manager).

## Quick Start

### For a New Machine

1. **Run the bootstrap script** to install Homebrew, essential tools, and set up your environment:
   ```bash
   ./bootstrap.sh
   ```

2. **Set up yadm** (if not using the bootstrap script):
   ```bash
   ./setup_yadm.sh
   ```

3. **Clone your dotfiles** (if stored in a remote repository):
   ```bash
   yadm clone <your-repo-url>
   ```

### For an Existing Setup

1. **List and categorize your dotfiles**:
   ```bash
   python3 list_dotfiles.py
   ```

2. **Add dotfiles to yadm**:
   ```bash
   yadm add ~/.zshrc
   yadm add ~/.gitconfig
   # ... add other files
   ```

3. **Commit and push**:
   ```bash
   yadm commit -m "Update dotfiles"
   yadm push
   ```

## Scripts Overview

### `bootstrap.sh`
Comprehensive bootstrap script that:
- Installs Homebrew (macOS)
- Installs essential tools (git, zsh, vim, tmux, etc.)
- Sets up zsh as default shell
- Installs Oh My Zsh
- Configures yadm
- Sets up Python and Node.js development environments
- Installs useful GUI applications (optional)

**Usage:**
```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

### `setup_yadm.sh`
Interactive script to set up yadm for dotfiles management:
- Checks for yadm installation and installs if needed
- Initializes yadm repository
- Analyzes existing dotfiles
- Helps add files to yadm
- Creates initial commit

**Usage:**
```bash
chmod +x setup_yadm.sh
./setup_yadm.sh
```

### `list_dotfiles.py`
Python script that analyzes and categorizes dotfiles in your home directory:
- **Safe to manage**: Configuration files that should be tracked
- **Unknown**: Files that need review before adding
- **Excluded**: Files that should NOT be managed (cache, history, sensitive data)

**Usage:**
```bash
python3 list_dotfiles.py
```

### `.yadm/bootstrap`
Automatic bootstrap script that runs when you:
- Clone your dotfiles: `yadm clone <repo-url>`
- Checkout your dotfiles: `yadm checkout`

This script automatically:
- Installs Homebrew (if on macOS)
- Installs essential tools
- Sets up zsh
- Installs Oh My Zsh
- Creates necessary directories
- Sets up development environments

## File Structure

```
dotfiles/
├── bootstrap.sh          # Main bootstrap script
├── setup_yadm.sh         # yadm setup helper
├── list_dotfiles.py      # Dotfiles analyzer
├── test_local.sh         # Local validation script
├── README.md             # This file
├── .github/
│   └── workflows/
│       └── test.yml      # CI/CD workflow for testing scripts
└── .yadm/
    └── bootstrap         # Automatic bootstrap (runs on clone/checkout)
```

## Common yadm Commands

```bash
# Initialize repository
yadm init

# Add files
yadm add ~/.zshrc
yadm add ~/.gitconfig

# Commit changes
yadm commit -m "Update dotfiles"

# Push to remote
yadm push

# Pull from remote
yadm pull

# Check status
yadm status

# List tracked files
yadm ls-files

# Clone on new machine
yadm clone <repo-url>
```

## Encryption

To encrypt sensitive files (like SSH keys or API tokens):

1. Create `.yadm/encrypt` file:
   ```bash
   echo ".ssh/id_rsa" >> .yadm/encrypt
   echo ".aws/credentials" >> .yadm/encrypt
   ```

2. yadm will automatically encrypt these files when committing.

See [yadm encryption documentation](https://yadm.io/docs/encryption) for more details.

## Best Practices

1. **Don't commit sensitive data**:
   - SSH private keys
   - API tokens
   - Passwords
   - Use encryption for sensitive files

2. **Exclude machine-specific files**:
   - Cache directories
   - History files
   - Temporary files
   - Use `.yadm/encrypt` or `.gitignore` to exclude them

3. **Use conditional includes**:
   - yadm supports OS-specific files (e.g., `.zshrc##os.Darwin`)
   - Use this for platform-specific configurations

4. **Keep bootstrap script updated**:
   - Update `.yadm/bootstrap` as your setup evolves
   - Test it on a fresh machine periodically

## Troubleshooting

### yadm not found
- macOS: `brew install yadm`
- Linux: See [yadm installation guide](https://yadm.io/docs/install)

### Bootstrap script fails
- Check that you have necessary permissions
- On macOS, you may need to allow Homebrew installation
- On Linux, you may need sudo for package installation

### Files not being tracked
- Check `yadm status` to see what's tracked
- Use `yadm add <file>` to explicitly add files
- Check `.yadm/encrypt` if files should be encrypted

## Testing

This repository includes GitHub Actions workflows to ensure scripts work correctly:

- **Syntax validation**: Checks that all bash scripts have valid syntax
- **Python linting**: Validates Python code quality
- **Script execution tests**: Verifies scripts can run without errors (dry-run mode)

The workflows run automatically on:
- Push to main/master branch
- Pull requests
- Manual workflow dispatch

View test results in the "Actions" tab of this repository.

**Note**: Update the badge URL in the README header with your actual GitHub username/repository.

### Local Testing

Run the local test script to validate everything before committing:

```bash
./test_local.sh
```

This script performs the same checks as the GitHub Actions workflow and helps catch issues early.

## CI/CD

The GitHub Actions workflow (`.github/workflows/test.yml`) tests:
- Bash script syntax validation
- Python script execution and output
- Script permissions and shebang lines
- Cross-platform compatibility checks

To run tests locally:
```bash
# Test bash scripts
bash -n bootstrap.sh
bash -n setup_yadm.sh
bash -n .yadm/bootstrap

# Test Python script
python3 -m py_compile list_dotfiles.py
python3 list_dotfiles.py
```

## Resources

- [yadm Documentation](https://yadm.io/docs/)
- [yadm GitHub](https://github.com/TheLocehiliosan/yadm)
- [Oh My Zsh](https://ohmyz.sh/)
- [GitHub Actions](https://docs.github.com/en/actions)

## Contributing

When making changes:
1. Test scripts locally before committing
2. Ensure GitHub Actions pass
3. Update documentation if needed
4. Follow shell scripting best practices

## License

This dotfiles setup is provided as-is. Feel free to use and modify for your needs.

