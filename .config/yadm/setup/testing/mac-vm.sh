#!/bin/sh
# New-Mac onboarding in a Tart macOS VM (cirruslabs sequoia-base), checking in to a hub run on this Mac.
# SOURCE=local (default) clones the current branch from a bare repo shared into the VM with tart --dir;
# SOURCE=github clones branch BRANCH from GitHub (it must be pushed). KEEP=1 keeps the VM; WORKTREE=1 see lib.sh.
set -eu
TESTING=$(cd "$(dirname "$0")" && pwd)
. "$TESTING/lib.sh"
SETUP=$(dirname "$TESTING")
IMAGE=sequoia-base
VM=converge-mac
LOG="$CACHE/mac-vm.log"
ASKPASS="$CACHE/askpass.sh"
GITHUB=https://github.com/jyesselm/dotfiles.git
# Inside the VM: brew and ~/.local/bin on PATH, and the hub through the ssh reverse tunnel.
VM_ENV='test -x /opt/homebrew/bin/brew && eval "$(/opt/homebrew/bin/brew shellenv)"; export PATH="$HOME/.local/bin:$PATH" CONVERGE_HUB=http://127.0.0.1:8790;'
HUB_PID=

# vssh COMMAND: run a shell command in the VM as admin (cirruslabs default admin/admin).
# -R forwards the VM's 127.0.0.1:8790 to the hub here, which listens on 127.0.0.1 only.
vssh() {
  SSH_ASKPASS="$ASKPASS" SSH_ASKPASS_REQUIRE=force \
    ssh -F /dev/null \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
    -o PubkeyAuthentication=no -o IdentityAgent=none -o ConnectTimeout=10 \
    -R 8790:127.0.0.1:8790 \
    "admin@$IP" "$VM_ENV $1" < /dev/null
}

# mvm COMMAND: vssh with the output appended to $LOG.
mvm() {
  echo "\$ $1" >> "$LOG"
  vssh "$1" >> "$LOG" 2>&1
}

write_askpass() {
  printf '#!/bin/sh\necho "%s"\n' "${VM_PASSWORD:-admin}" > "$ASKPASS"
  chmod 700 "$ASKPASS"
}

have_image() {
  tart list | grep -qw "$IMAGE"
}

start_vm() {
  if ! tart list | grep -qw "$VM"; then
    tart clone "$IMAGE" "$VM"
  fi
  if ! tart list | grep -w "$VM" | grep -qw running; then
    tart run --no-graphics "--dir=testing:$CACHE:ro" "$VM" > "$CACHE/tart-run.log" 2>&1 &
  fi
  IP=$(tart ip --wait 300 "$VM")
}

wait_ssh() {
  for i in $(seq 60); do
    if mvm true; then
      return 0
    fi
    sleep 5
  done
  return 1
}

start_hub() {
  python3 "$SETUP/hub.py" serve --port 8790 --db "$CACHE/mac-hub.sqlite" --bridge none --trust-local > "$CACHE/mac-hub.log" 2>&1 &
  HUB_PID=$!
  for i in $(seq 10); do
    if curl -fsS http://127.0.0.1:8790/fleet > /dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_hub() {
  if [ -n "$HUB_PID" ]; then
    kill "$HUB_PID" 2> /dev/null || true
  fi
}

install_homebrew() {
  mvm 'test -x /opt/homebrew/bin/brew || NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
}

clone_url() {
  if [ "${SOURCE:-local}" = github ]; then
    echo "$GITHUB"
  else
    echo '~/testing-remote/remote.git'
  fi
}

clone() {
  mvm "ln -sfn '/Volumes/My Shared Files/testing' ~/testing-remote"
  mvm "$(clone_script "$(clone_url)")"
}

fleet_lists_vm() {
  name=$(vssh 'hostname -s')
  curl -fsS http://127.0.0.1:8790/fleet | fleet_has "$name"
}

stop() {
  stop_hub
  if [ "${KEEP:-0}" != 1 ]; then
    tart stop "$VM" || true
    tart delete "$VM"
  fi
  echo "log in $LOG"
}

mkdir -p "$CACHE"
: > "$LOG"
if ! have_image; then
  fail "tart image $IMAGE present (tart list)"
  finish
fi
trap stop_hub EXIT
write_askpass
build_remote
start_vm
check "ssh admin@$IP" wait_ssh
check "[phase1] hub on this Mac answers /fleet" start_hub
check "Homebrew installed" install_homebrew
check "brew install yadm python" mvm "brew install yadm python"
check "yadm clone ($(clone_url))" clone
check "class laptop" mvm "yadm config local.class laptop && yadm alt"
check "bootstrap --plan" mvm "~/.config/yadm/bootstrap --plan"
check "yadm bootstrap" mvm "yadm bootstrap"
check "converge sync --plan reaches the summary" mvm "converge sync --plan | grep -q '^Summary'"
check "converge sync writes last.json" mvm "converge sync; test -f ~/.local/state/dotfiles/sync/last.json"
check "converge status shows the sync" mvm "converge status | grep -q '^Last sync'"
check "converge schedule" mvm "converge schedule"
check "launchd job loaded" mvm 'launchctl print "gui/$(id -u)/com.yesselman.dotfiles-sync" > /dev/null'
check "[phase1] hub /fleet lists the VM" fleet_lists_vm
stop
finish
