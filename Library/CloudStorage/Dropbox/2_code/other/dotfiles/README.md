# Dotfiles Setup with yadm

This repository contains setup scripts and configuration for managing dotfiles with [yadm](https://yadm.io/) (Yet Another Dotfiles Manager).

## Quick Start

1. **Install yadm** (if not already installed):
   ```bash
   brew install yadm  # macOS
   # or see https://yadm.io/docs/install for other platforms
   ```

2. **List your dotfiles**:
   ```bash
   python3 list_dotfiles.py
   ```

3. **Run the setup script**:
   ```bash
   chmod +x setup_yadm.sh
   ./setup_yadm.sh
   ```

4. **Initialize yadm repository**:
   ```bash
   yadm init
   ```

5. **Add your dotfiles**:
   ```bash
   yadm add ~/.zshrc
   yadm add ~/.gitconfig
   yadm add ~/.taskrc
   # ... add other files as needed
   ```

6. **Create initial commit**:
   ```bash
   yadm commit -m "Initial dotfiles commit"
   ```

7. **Add remote repository** (optional):
   ```bash
   yadm remote add origin <your-git-repo-url>
   yadm push -u origin master
   ```

## Files in this Repository

- `list_dotfiles.py`: Python script to analyze and categorize dotfiles in your home directory
- `setup_yadm.sh`: Interactive setup script for yadm
- `.yadm/`: yadm configuration directory
  - `encrypt`: Configuration for encrypting sensitive files
  - `bootstrap`: Script that runs automatically on new machines
  - `README.md`: Documentation for yadm configuration

## Common yadm Commands

```bash
# Initialize repository
yadm init

# Add files
yadm add ~/.zshrc

# Commit changes
yadm commit -m "Update dotfiles"

# Push to remote
yadm push

# Clone on new machine
yadm clone <repo-url>

# Check status
yadm status

# Show differences
yadm diff
```

## Managing Different Machines

yadm supports alternate files for different machines. Create files like:
- `.zshrc##machine1`
- `.zshrc##machine2`

yadm will automatically use the correct file based on the hostname.

## Encryption

To encrypt sensitive files, edit `.yadm/encrypt` and list the files you want encrypted. yadm will use git-crypt or transcrypt for encryption.

## More Information

- [yadm Documentation](https://yadm.io/docs/)
- [yadm GitHub](https://github.com/TheLocehiliosan/yadm)

