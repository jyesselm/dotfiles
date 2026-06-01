# ~/.zshenv — sourced by EVERY zsh invocation, including non-interactive ones
# (e.g. `zsh -c`, scripts, and Claude Code's Bash tool), unlike ~/.zshrc.

# Silence zoxide's "doctor" warning everywhere. It fires from the `cd` wrapper in
# non-interactive shells (Claude Code, scripts) that load zoxide's functions via a
# snapshot but don't re-register its chpwd hook. Setting this in .zshrc only fixed
# interactive shells; .zshenv covers the rest.
export _ZO_DOCTOR=0
