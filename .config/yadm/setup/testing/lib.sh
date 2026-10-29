# Shared helpers for the converge test scripts; sourced, not run.
# REMOTE: a bare repo holding the current yadm branch (plus the uncommitted work tree with WORKTREE=1).

CACHE="$HOME/.cache/converge-testing"
REMOTE="$CACHE/remote.git"
BRANCH="${BRANCH:-$(yadm rev-parse --abbrev-ref HEAD)}"
FAILS=0

pass() {
  echo "PASS $1"
}

fail() {
  echo "FAIL $1"
  FAILS=$((FAILS + 1))
}

# check "what" command args...: PASS when the command exits 0.
check() {
  what="$1"
  shift
  if "$@"; then
    pass "$what"
  else
    fail "$what"
  fi
}

finish() {
  if [ "$FAILS" -gt 0 ]; then
    echo "$FAILS assertion(s) failed"
    exit 1
  fi
  echo "all assertions passed"
}

remote_git() {
  git --git-dir="$REMOTE" "$@"
}

# Commit the uncommitted dotfiles setup on top of BRANCH, in REMOTE only (the yadm repo is not touched).
overlay_worktree() {
  index="$CACHE/overlay-index"
  rm -f "$index"
  (
    cd "$HOME"
    export GIT_INDEX_FILE="$index"
    remote_git --work-tree="$HOME" read-tree "$BRANCH"
    remote_git --work-tree="$HOME" add --update -- .config/yadm .local/bin
    remote_git --work-tree="$HOME" add -- .config/yadm/setup ':(exclude)*.pyc'
    tree=$(remote_git write-tree)
    commit=$(remote_git -c user.name=converge-testing -c user.email=testing@localhost \
      commit-tree "$tree" -p "$BRANCH" -m "work tree snapshot for testing")
    remote_git update-ref "refs/heads/$BRANCH" "$commit"
  )
  rm -f "$index"
}

build_remote() {
  mkdir -p "$CACHE"
  if [ ! -d "$REMOTE" ]; then
    git init --quiet --bare "$REMOTE"
  fi
  remote_git fetch --quiet --force "$(yadm rev-parse --git-dir)" "+refs/heads/$BRANCH:refs/heads/$BRANCH"
  remote_git symbolic-ref HEAD "refs/heads/$BRANCH"
  if [ "${WORKTREE:-0}" = 1 ]; then
    overlay_worktree
  fi
  echo "remote $REMOTE at $BRANCH $(remote_git rev-parse --short "$BRANCH")"
}

# clone_script URL: shell text that clones BRANCH with yadm, or resets an existing clone to it (KEEP=1 reruns).
clone_script() {
  echo "if [ -d ~/.local/share/yadm/repo.git ]; then yadm fetch --force origin && yadm checkout --force -B $BRANCH origin/$BRANCH; else yadm clone --no-bootstrap -b $BRANCH $1; fi"
}

# fleet_has HOST [EXIT] < /fleet JSON
fleet_has() {
  python3 "$TESTING/json_check.py" fleet "$@"
}

# machine_has KEY... < /machine/<host> JSON
machine_has() {
  python3 "$TESTING/json_check.py" keys "$@"
}
