# ~/.zsh/macos.zsh
# macOS-specific configuration (loaded only on Mac)

# ============================================================
# Environment
# ============================================================
export COLORTERM=truecolor

# ============================================================
# Homebrew Shell Plugins
# ============================================================
[[ -f /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && \
  source /opt/homebrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

[[ -f /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && \
  source /opt/homebrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh

# ============================================================
# Mamba/Conda (Homebrew installation)
# ============================================================
if [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh" ]]; then
  source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/conda.sh"
  [[ -f "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh" ]] && \
    source "/opt/homebrew/Caskroom/mambaforge/base/etc/profile.d/mamba.sh"
elif command -v mamba &>/dev/null; then
  export MAMBA_ROOT_PREFIX="$HOME/micromamba"
  eval "$(mamba shell hook --shell zsh)"
fi

mamba activate py3 2>/dev/null

# Force conda/mamba paths to front
if [[ -n "$CONDA_PREFIX" ]]; then
  export PATH="$CONDA_PREFIX/bin:${PATH//$CONDA_PREFIX\/bin:/}"
fi
