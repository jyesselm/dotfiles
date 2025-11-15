#!/usr/bin/env python3
"""
Script to list and categorize dotfiles in the home directory.
Helps identify which dotfiles should be managed by yadm.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict

# Files/directories to exclude from dotfile management
EXCLUDE = {
    '.DS_Store',
    '.Trash',
    '.cache',
    '.dropbox',
    '.local',
    '.ssh',  # Usually contains sensitive keys
    '.zcompdump',
    '.zcompdump-*',
    '.zsh_history',
    '.bash_history',
    '.python_history',
    '.viminfo',
    '.lesshst',
    '.wget-hsts',
    '.CFUserTextEncoding',
    '.zsh_sessions',
    '.bash_sessions',
    '.vim-bookmarks',
    '.cookiecutter_replay',
    '.cpanm',
    '.cups',
    '.docker',
    '.npm',
    '.nextflow',
    '.mamba',
    '.conda',
    '.ipython',
    '.matplotlib',
    '.pymol',
    '.task',  # Taskwarrior data directory
    '.cursor',
    '.cursor-tutor',
    '.yarn',
    '.yarnrc',
    '.node_repl_history',
    '.npmrc',  # May contain tokens
    '.pypirc',  # May contain credentials
    '.netrc',  # Contains credentials
    '.aws',  # Contains credentials
    '.password-store',
    '.gnupg',  # Contains keys
}

# Files that are typically safe to manage
SAFE_TO_MANAGE = {
    '.zshrc',
    '.bashrc',
    '.bash_profile',
    '.gitconfig',
    '.gitignore_global',
    '.vimrc',
    '.vim',
    '.tmux.conf',
    '.taskrc',
    '.condarc',
    '.pymolrc',
    '.config',
    '.oh-my-zsh',
    '.zsh',
    '.jupyter',
    '.zprofile',
    '.zshenv',
    '.zlogin',
    '.gitattributes',
    '.nvim',
    '.editorconfig',
    '.prettierrc',
    '.prettierrc.json',
    '.eslintrc',
    '.eslintrc.json',
    '.flake8',
    '.pylintrc',
    '.mypy.ini',
    '.pythonrc',
    '.inputrc',
    '.screenrc',
    '.ackrc',
    '.agignore',
    '.rgignore',
    '.ripgreprc',
    '.curlrc',
    '.wgetrc',
    '.gemrc',
    '.irbrc',
    '.pryrc',
    '.railsrc',
    '.rspec',
    '.rubocop.yml',
    '.tmuxinator',
    '.dockerignore',
}

def should_exclude(name: str) -> bool:
    """Check if a file/directory should be excluded."""
    if name in EXCLUDE:
        return True
    # Check for patterns
    for pattern in EXCLUDE:
        if '*' in pattern:
            prefix = pattern.replace('*', '')
            if name.startswith(prefix):
                return True
    return False

def get_file_size(path: Path) -> str:
    """Get human-readable file size."""
    try:
        if path.is_file():
            size = path.stat().st_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        elif path.is_dir():
            # For directories, count files (approximate)
            try:
                count = sum(1 for _ in path.rglob('*') if _.is_file())
                return f"{count} files"
            except (PermissionError, OSError):
                return "N/A"
    except (OSError, PermissionError):
        return "N/A"
    return "N/A"

def categorize_dotfiles() -> Dict[str, List[Tuple[str, bool, str]]]:
    """List and categorize all dotfiles in home directory.
    
    Returns:
        Dictionary with keys 'safe', 'unknown', 'excluded', each containing
        lists of tuples (name, is_dir, size_info).
    """
    home = Path.home()
    dotfiles = defaultdict(list)
    
    try:
        # Find all dotfiles
        for item in home.iterdir():
            if item.name.startswith('.'):
                name = item.name
                try:
                    is_dir = item.is_dir()
                    size_info = get_file_size(item)
                    
                    if should_exclude(name):
                        dotfiles['excluded'].append((name, is_dir, size_info))
                    elif name in SAFE_TO_MANAGE:
                        dotfiles['safe'].append((name, is_dir, size_info))
                    else:
                        dotfiles['unknown'].append((name, is_dir, size_info))
                except (PermissionError, OSError) as e:
                    # Skip files we can't access
                    dotfiles['excluded'].append((name, False, "permission denied"))
    except PermissionError:
        print("Error: Permission denied accessing home directory", file=sys.stderr)
        sys.exit(1)
    
    return dotfiles

def main():
    """Main function to display categorized dotfiles."""
    print("=" * 80)
    print("DOTFILES INVENTORY")
    print("=" * 80)
    print()
    
    try:
        dotfiles = categorize_dotfiles()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("✅ SAFE TO MANAGE (Recommended for yadm):")
    print("-" * 80)
    if dotfiles['safe']:
        for name, is_dir, size_info in sorted(dotfiles['safe']):
            item_type = "📁 DIR" if is_dir else "📄 FILE"
            print(f"  {item_type:8} {name:30} ({size_info})")
    else:
        print("  (none)")
    print()
    
    print("⚠️  UNKNOWN (Review before adding to yadm):")
    print("-" * 80)
    if dotfiles['unknown']:
        for name, is_dir, size_info in sorted(dotfiles['unknown']):
            item_type = "📁 DIR" if is_dir else "📄 FILE"
            print(f"  {item_type:8} {name:30} ({size_info})")
    else:
        print("  (none)")
    print()
    
    print("❌ EXCLUDED (Should NOT be managed by yadm):")
    print("-" * 80)
    if dotfiles['excluded']:
        # Only show first 20 excluded items to avoid clutter
        excluded_list = sorted(dotfiles['excluded'])[:20]
        for name, is_dir, size_info in excluded_list:
            item_type = "📁 DIR" if is_dir else "📄 FILE"
            print(f"  {item_type:8} {name:30} ({size_info})")
        if len(dotfiles['excluded']) > 20:
            print(f"  ... and {len(dotfiles['excluded']) - 20} more excluded items")
    else:
        print("  (none)")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Safe to manage:     {len(dotfiles['safe'])}")
    print(f"  Unknown (review):   {len(dotfiles['unknown'])}")
    print(f"  Excluded:           {len(dotfiles['excluded'])}")
    print()
    
    # Generate yadm add commands
    if dotfiles['safe']:
        print("Suggested yadm commands:")
        print("-" * 80)
        for name, is_dir, _ in sorted(dotfiles['safe']):
            print(f"  yadm add ~/{name}")
        print()
        
        # Generate a script to add all safe files
        print("Or run this to add all safe files at once:")
        print("-" * 80)
        safe_names = [name for name, _, _ in sorted(dotfiles['safe'])]
        print(f"  yadm add {' '.join(f'~/{name}' for name in safe_names)}")
        print()

if __name__ == '__main__':
    main()

