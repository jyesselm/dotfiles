#!/bin/bash
# Setup script for yadm (Yet Another Dotfiles Manager)
# This script helps initialize and configure yadm for dotfiles management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running on macOS
is_macos() {
    [[ "$OSTYPE" == "darwin"* ]]
}

# Check if running on Linux
is_linux() {
    [[ "$OSTYPE" == "linux-gnu"* ]]
}

echo "=========================================="
echo "  yadm Dotfiles Setup"
echo "=========================================="
echo ""

# Check if yadm is installed
if ! command -v yadm &> /dev/null; then
    log_error "yadm is not installed."
    echo ""
    echo "Installation options:"
    echo "  macOS (Homebrew):  brew install yadm"
    echo "  Linux:             See https://yadm.io/docs/install"
    echo ""
    read -p "Would you like to install yadm now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if is_macos && command -v brew &> /dev/null; then
            log_info "Installing yadm via Homebrew..."
            brew install yadm
            log_success "yadm installed successfully"
        elif is_linux; then
            # Try to install via package manager
            if command -v apt-get &> /dev/null; then
                log_info "Installing yadm via apt-get..."
                sudo apt-get update
                sudo apt-get install -y yadm || {
                    log_warning "apt-get installation failed, trying manual installation..."
                    sudo curl -fsSLo /usr/local/bin/yadm https://github.com/TheLocehiliosan/yadm/raw/master/yadm
                    sudo chmod +x /usr/local/bin/yadm
                }
            elif command -v pacman &> /dev/null; then
                log_info "Installing yadm via pacman..."
                sudo pacman -S --noconfirm yadm
            else
                log_error "Please install yadm manually. Visit: https://yadm.io/docs/install"
                exit 1
            fi
            log_success "yadm installed successfully"
        else
            log_error "Please install yadm manually. Visit: https://yadm.io/docs/install"
            exit 1
        fi
    else
        log_error "Please install yadm first, then run this script again."
        exit 1
    fi
else
    log_success "yadm is installed: $(which yadm)"
    yadm --version
    echo ""
fi

# Check if yadm repo is already initialized
if yadm rev-parse --git-dir &> /dev/null; then
    log_warning "yadm repository already exists."
    echo ""
    read -p "Would you like to reinitialize? This will not delete your files. (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Reinitializing yadm repository..."
        yadm init
        log_success "Repository reinitialized"
    fi
else
    log_info "yadm repository not found. Ready to initialize."
    echo ""
    read -p "Would you like to initialize yadm now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Initializing yadm repository..."
        yadm init
        log_success "Repository initialized"
        
        # Ask about remote
        read -p "Would you like to add a remote repository? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter remote URL: " remote_url
            if [ -n "$remote_url" ]; then
                yadm remote add origin "$remote_url"
                log_success "Remote added: $remote_url"
            fi
        fi
    fi
    echo ""
fi

# Run the Python script to list dotfiles
if [ -f "list_dotfiles.py" ]; then
    echo "=========================================="
    echo "Analyzing your dotfiles..."
    echo "=========================================="
    python3 list_dotfiles.py
    echo ""
    
    # Ask if user wants to add safe files
    if yadm rev-parse --git-dir &> /dev/null; then
        read -p "Would you like to add all 'safe to manage' files to yadm? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Adding safe files to yadm..."
            # Get safe files from Python script output (simplified approach)
            python3 list_dotfiles.py | grep "yadm add" | sed 's/^  //' | while read cmd; do
                eval "$cmd" || log_warning "Failed to add file"
            done
            log_success "Files added to yadm"
            
            read -p "Would you like to create an initial commit? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                yadm commit -m "Initial dotfiles commit"
                log_success "Initial commit created"
            fi
        fi
    fi
fi

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
if ! yadm rev-parse --git-dir &> /dev/null; then
    echo "1. Initialize yadm repository:"
    echo "   yadm init"
    echo ""
fi
echo "2. Add your dotfiles (if not done already):"
echo "   yadm add ~/.zshrc"
echo "   yadm add ~/.gitconfig"
echo "   # ... add other files as needed"
echo ""
echo "3. Create commits:"
echo "   yadm commit -m 'Add dotfiles'"
echo ""
echo "4. (Optional) Push to remote:"
echo "   yadm push -u origin master"
echo ""
echo "5. (Optional) Set up encryption for sensitive files:"
echo "   Edit .yadm/encrypt to list files that should be encrypted"
echo "   See: https://yadm.io/docs/encryption"
echo ""
echo "6. (Optional) Customize bootstrap script:"
echo "   Edit .yadm/bootstrap to automate setup on new machines"
echo ""


