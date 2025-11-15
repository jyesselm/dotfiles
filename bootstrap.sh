#!/bin/bash
# Comprehensive bootstrap script for setting up a new macOS/Linux machine
# This script installs Homebrew, essential tools, and sets up dotfiles

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Install Homebrew on macOS
install_homebrew() {
    if is_macos; then
        if command -v brew &> /dev/null; then
            log_success "Homebrew is already installed"
            brew update
        else
            log_info "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            
            # Add Homebrew to PATH for Apple Silicon Macs
            if [[ -f "/opt/homebrew/bin/brew" ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [[ -f "/usr/local/bin/brew" ]]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
            
            log_success "Homebrew installed successfully"
        fi
    else
        log_warning "Not on macOS, skipping Homebrew installation"
    fi
}

# Install essential tools via Homebrew (macOS) or package manager (Linux)
install_essential_tools() {
    log_info "Installing essential tools..."
    
    if is_macos; then
        # Essential tools for macOS
        local tools=(
            "git"
            "yadm"
            "zsh"
            "vim"
            "tmux"
            "curl"
            "wget"
            "jq"
            "tree"
            "htop"
            "ripgrep"
            "fd"
            "bat"
            "exa"
        )
        
        for tool in "${tools[@]}"; do
            if brew list "$tool" &> /dev/null; then
                log_info "$tool is already installed"
            else
                log_info "Installing $tool..."
                brew install "$tool" || log_warning "Failed to install $tool"
            fi
        done
        
        # Install useful casks
        log_info "Installing useful applications..."
        local casks=(
            "iterm2"
            "visual-studio-code"
            "google-chrome"
            "firefox"
            "slack"
            "spotify"
        )
        
        read -p "Would you like to install GUI applications? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for cask in "${casks[@]}"; do
                if brew list --cask "$cask" &> /dev/null; then
                    log_info "$cask is already installed"
                else
                    log_info "Installing $cask..."
                    brew install --cask "$cask" || log_warning "Failed to install $cask"
                fi
            done
        fi
        
    elif is_linux; then
        log_info "Detected Linux system"
        
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            log_info "Using apt-get (Debian/Ubuntu)"
            sudo apt-get update
            sudo apt-get install -y git zsh vim tmux curl wget jq tree htop ripgrep fd-find bat exa
            
            # Install yadm
            if ! command -v yadm &> /dev/null; then
                log_info "Installing yadm..."
                sudo apt-get install -y yadm || {
                    # Fallback to manual installation
                    log_info "Installing yadm manually..."
                    sudo curl -fsSLo /usr/local/bin/yadm https://github.com/TheLocehiliosan/yadm/raw/master/yadm
                    sudo chmod +x /usr/local/bin/yadm
                }
            fi
            
        elif command -v yum &> /dev/null; then
            log_info "Using yum (RHEL/CentOS)"
            sudo yum install -y git zsh vim tmux curl wget jq tree htop
            
        elif command -v pacman &> /dev/null; then
            log_info "Using pacman (Arch Linux)"
            sudo pacman -S --noconfirm git zsh vim tmux curl wget jq tree htop ripgrep fd bat exa yadm
            
        else
            log_warning "Unknown Linux distribution. Please install tools manually."
        fi
    fi
    
    log_success "Essential tools installation complete"
}

# Set up zsh as default shell
setup_zsh() {
    if command -v zsh &> /dev/null; then
        current_shell=$(echo $SHELL)
        zsh_path=$(which zsh)
        
        if [[ "$current_shell" != "$zsh_path" ]]; then
            log_info "Setting zsh as default shell..."
            if is_macos; then
                # On macOS, we need to add zsh to /etc/shells first
                if ! grep -q "$zsh_path" /etc/shells; then
                    echo "$zsh_path" | sudo tee -a /etc/shells
                fi
            fi
            chsh -s "$zsh_path"
            log_success "zsh set as default shell (restart terminal to take effect)"
        else
            log_success "zsh is already the default shell"
        fi
    else
        log_warning "zsh is not installed"
    fi
}

# Install Oh My Zsh if not present
install_oh_my_zsh() {
    if [ ! -d "$HOME/.oh-my-zsh" ]; then
        log_info "Installing Oh My Zsh..."
        sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
        log_success "Oh My Zsh installed"
    else
        log_success "Oh My Zsh is already installed"
    fi
}

# Set up yadm and dotfiles
setup_yadm() {
    if ! command -v yadm &> /dev/null; then
        log_error "yadm is not installed. Please run the essential tools installation first."
        return 1
    fi
    
    log_info "Setting up yadm..."
    
    # Check if yadm repo is already initialized
    if [ -d "$HOME/.config/yadm" ] || [ -d "$HOME/.local/share/yadm/repo.git" ]; then
        log_warning "yadm repository already exists"
        read -p "Would you like to reinitialize? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Reinitializing yadm repository..."
            yadm init
        fi
    else
        log_info "Initializing yadm repository..."
        yadm init
        
        # If we're in a dotfiles directory, set it as the remote
        if [ -d ".git" ] || [ -d ".yadm" ]; then
            log_info "Detected existing dotfiles repository"
            read -p "Would you like to add this directory as a remote? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                read -p "Enter remote URL (or press Enter to skip): " remote_url
                if [ -n "$remote_url" ]; then
                    yadm remote add origin "$remote_url"
                    log_success "Remote added: $remote_url"
                fi
            fi
        fi
    fi
    
    log_success "yadm setup complete"
}

# Install Python development tools
setup_python() {
    log_info "Setting up Python development environment..."
    
    if is_macos; then
        if ! command -v python3 &> /dev/null; then
            log_info "Installing Python via Homebrew..."
            brew install python@3.11
        fi
        
        # Install pip packages
        if command -v pip3 &> /dev/null; then
            log_info "Installing Python packages..."
            pip3 install --upgrade pip
            pip3 install --user \
                ipython \
                jupyter \
                black \
                flake8 \
                mypy \
                pytest \
                virtualenv \
                pipenv \
                poetry
            log_success "Python packages installed"
        fi
    fi
}

# Install Node.js and npm
setup_nodejs() {
    log_info "Setting up Node.js..."
    
    if is_macos; then
        if ! command -v node &> /dev/null; then
            log_info "Installing Node.js via Homebrew..."
            brew install node
        else
            log_success "Node.js is already installed: $(node --version)"
        fi
        
        # Install global npm packages
        if command -v npm &> /dev/null; then
            log_info "Installing global npm packages..."
            npm install -g \
                yarn \
                pnpm \
                typescript \
                ts-node \
                eslint \
                prettier \
                nodemon \
                http-server
            log_success "npm packages installed"
        fi
    fi
}

# Main bootstrap function
main() {
    echo "=========================================="
    echo "  Dotfiles Bootstrap Script"
    echo "=========================================="
    echo ""
    
    # Detect OS
    if is_macos; then
        log_info "Detected macOS"
    elif is_linux; then
        log_info "Detected Linux"
    else
        log_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    echo ""
    
    # Step 1: Install Homebrew (macOS only)
    if is_macos; then
        read -p "Install/update Homebrew? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_homebrew
            echo ""
        fi
    fi
    
    # Step 2: Install essential tools
    read -p "Install essential tools? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_essential_tools
        echo ""
    fi
    
    # Step 3: Set up zsh
    read -p "Set up zsh as default shell? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_zsh
        echo ""
    fi
    
    # Step 4: Install Oh My Zsh
    read -p "Install Oh My Zsh? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_oh_my_zsh
        echo ""
    fi
    
    # Step 5: Set up yadm
    read -p "Set up yadm for dotfiles management? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_yadm
        echo ""
    fi
    
    # Step 6: Set up Python
    read -p "Set up Python development environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_python
        echo ""
    fi
    
    # Step 7: Set up Node.js
    read -p "Set up Node.js? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_nodejs
        echo ""
    fi
    
    echo "=========================================="
    log_success "Bootstrap complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Restart your terminal to apply shell changes"
    echo "  2. Run 'yadm add ~/.zshrc' to add your dotfiles"
    echo "  3. Run 'yadm commit -m \"Initial commit\"'"
    echo "  4. Run 'yadm remote add origin <your-repo-url>' (if using git)"
    echo "  5. Run 'yadm push -u origin master' (if using git)"
    echo ""
}

# Run main function
main "$@"

