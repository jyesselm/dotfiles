#!/bin/sh
# home-gpu rehearsal in an OrbStack Ubuntu VM: real systemd user session, bootstrap, hub unit, sync, schedule.
# KEEP=1 keeps the VM (the next run reuses it); WORKTREE=1 tests uncommitted changes too (see lib.sh).
set -eu
TESTING=$(cd "$(dirname "$0")" && pwd)
. "$TESTING/lib.sh"
VM=converge-test
LOG="$CACHE/linux-vm.log"
# The Mac file system appears inside OrbStack VMs under /mnt/mac.
VM_REMOTE="/mnt/mac$REMOTE"

# vm COMMAND: run a shell command in the VM as the default user, output appended to $LOG.
vm() {
  echo "\$ $1" >> "$LOG"
  orb -m "$VM" bash -c "export PATH=\$HOME/.local/bin:\$PATH CONVERGE_HUB=http://127.0.0.1:8790; $1" >> "$LOG" 2>&1
}

create_vm() {
  if ! orb info "$VM" > /dev/null 2>&1; then
    orb create ubuntu:24.04 "$VM"
  fi
}

prepare() {
  vm "sudo apt-get update -qq && sudo apt-get install -y -qq python3 git yadm curl cron"
  # Linger starts the user manager at boot, which is what gives systemctl --user a bus here.
  vm "sudo loginctl enable-linger \$USER"
}

clone() {
  vm "$(clone_script "$VM_REMOTE")"
}

# local.hostname makes yadm pick the ##hostname.home-gpu alternates (the hub unit).
configure() {
  vm "yadm config local.class linux && yadm config local.hostname home-gpu && yadm alt"
}

hub_unit() {
  vm "systemctl --user daemon-reload && systemctl --user enable --now converge-hub"
}

hub_answers() {
  vm "for i in 1 2 3 4 5 6 7 8 9 10; do curl -fsS http://127.0.0.1:8790/fleet && exit 0; sleep 1; done; exit 1"
}

fleet_lists_vm() {
  orb -m "$VM" curl -fsS http://127.0.0.1:8790/fleet | fleet_has "$VM"
}

stop() {
  if [ "${KEEP:-0}" != 1 ]; then
    orb delete --force "$VM"
  fi
  echo "log in $LOG"
}

mkdir -p "$CACHE"
: > "$LOG"
build_remote
create_vm
check "VM packages and linger" prepare
check "yadm clone from the Mac bare repo" clone
check "class linux, hostname home-gpu" configure
check "bootstrap --plan" vm "~/.config/yadm/bootstrap --plan"
check "yadm bootstrap" vm "yadm bootstrap"
check "[phase1] converge-hub.service linked by yadm alt" vm "test -e ~/.config/systemd/user/converge-hub.service"
check "[phase1] systemctl --user enable --now converge-hub" hub_unit
check "[phase1] hub answers /fleet" hub_answers
check "converge sync --plan reaches the summary" vm "converge sync --plan | grep -q '^Summary'"
check "converge sync writes last.json" vm "converge sync; test -f ~/.local/state/dotfiles/sync/last.json"
check "converge status shows the sync" vm "converge status | grep -q '^Last sync'"
check "[phase1] hub /fleet lists $VM" fleet_lists_vm
check "converge schedule" vm "converge schedule"
check "crontab has the daily line" vm "crontab -l | grep -q 'dotfiles-sync'"
stop
finish
