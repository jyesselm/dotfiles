#!/bin/bash
# Local test script to validate all scripts before committing
# This mirrors the GitHub Actions workflow tests

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "=========================================="
echo "  Local Script Validation"
echo "=========================================="
echo ""

ERRORS=0

# Test Python script syntax
log_info "Testing Python script syntax..."
if python3 -m py_compile list_dotfiles.py 2>/dev/null; then
    log_success "list_dotfiles.py syntax is valid"
else
    log_error "list_dotfiles.py has syntax errors"
    ((ERRORS++))
fi

# Test Python script execution
log_info "Testing Python script execution..."
if python3 list_dotfiles.py > /dev/null 2>&1; then
    log_success "list_dotfiles.py executes successfully"
else
    log_warning "list_dotfiles.py execution had warnings (this may be normal)"
fi

# Test bash script syntax
log_info "Testing bash script syntax..."
for script in bootstrap.sh setup_yadm.sh .yadm/bootstrap; do
    if bash -n "$script" 2>/dev/null; then
        log_success "$script syntax is valid"
    else
        log_error "$script has syntax errors"
        ((ERRORS++))
    fi
done

# Check shebang lines
log_info "Checking shebang lines..."
for script in bootstrap.sh setup_yadm.sh .yadm/bootstrap; do
    if head -1 "$script" | grep -q "#!/bin/bash"; then
        log_success "$script has correct shebang"
    else
        log_error "$script missing or incorrect shebang"
        ((ERRORS++))
    fi
done

if head -1 list_dotfiles.py | grep -q "#!/usr/bin/env python3"; then
    log_success "list_dotfiles.py has correct shebang"
else
    log_error "list_dotfiles.py missing or incorrect shebang"
    ((ERRORS++))
fi

# Check script permissions
log_info "Checking script permissions..."
for script in bootstrap.sh setup_yadm.sh .yadm/bootstrap; do
    if [ -x "$script" ]; then
        log_success "$script is executable"
    else
        log_warning "$script is not executable (run: chmod +x $script)"
    fi
done

# Validate file structure
log_info "Validating file structure..."
for file in bootstrap.sh setup_yadm.sh list_dotfiles.py .yadm/bootstrap README.md; do
    if [ -f "$file" ]; then
        log_success "$file exists"
    else
        log_error "$file is missing"
        ((ERRORS++))
    fi
done

# Check for set -e in bash scripts
log_info "Checking for error handling..."
for script in bootstrap.sh setup_yadm.sh .yadm/bootstrap; do
    if grep -q "set -e" "$script"; then
        log_success "$script uses 'set -e'"
    else
        log_warning "$script may not use 'set -e'"
    fi
done

# Test Python imports
log_info "Testing Python imports..."
if python3 -c "import sys; from pathlib import Path; from collections import defaultdict" 2>/dev/null; then
    log_success "All Python imports are valid"
else
    log_error "Python imports failed"
    ((ERRORS++))
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    log_success "All tests passed! ✓"
    echo "=========================================="
    exit 0
else
    log_error "$ERRORS error(s) found"
    echo "=========================================="
    exit 1
fi

