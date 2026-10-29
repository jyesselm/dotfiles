#!/bin/sh
# End-to-end fleet test in Docker: clone, sync and check in from three clients, read them back from the hub.
# KEEP=1 leaves the containers up; WORKTREE=1 tests uncommitted changes too (see lib.sh).
set -eu
TESTING=$(cd "$(dirname "$0")" && pwd)
. "$TESTING/lib.sh"
export BRANCH
SKIP=packages,repos,apps,defaults,hotkeys
LOGS="$CACHE/e2e"

compose() {
  docker compose --project-directory "$TESTING" --file "$TESTING/compose.yml" "$@"
}

# on SERVICE COMMAND: run a shell command as joe in a running client, output to $LOGS/SERVICE.log.
on() {
  echo "\$ $2" >> "$LOGS/$1.log"
  compose exec -T "$1" bash -c "$2" >> "$LOGS/$1.log" 2>&1
}

hub_get() {
  compose exec -T hub curl -fsS "http://127.0.0.1:8790$1"
}

seed_remote() {
  compose run --rm --no-deps --user root --volume "$REMOTE:/src:ro" linux-a \
    sh -c 'git -c safe.directory="*" clone --quiet --bare /src /remote && chown -R joe:joe /remote'
}

start() {
  mkdir -p "$LOGS"
  rm -f "$LOGS"/*.log
  compose down --volumes --remove-orphans
  compose build --quiet
  build_remote
  seed_remote
  compose up --detach
}

client() {
  service=$1
  class=$2
  check "$service: yadm clone" on "$service" "yadm clone --no-bootstrap -b $BRANCH file:///remote && test -f ~/.config/yadm/setup/setup.py"
  check "$service: class $class" on "$service" "yadm config local.class $class && yadm alt && test \"\$(yadm config local.class)\" = $class"
  check "$service: converge sync --plan reaches the summary" on "$service" "converge sync --plan > /tmp/plan.log 2>&1; cat /tmp/plan.log; grep -q '^Summary' /tmp/plan.log"
  check "[phase1] $service: converge sync --skip $SKIP exits 0" on "$service" "converge sync --skip $SKIP"
  check "[phase1] $service: converge status shows the sync" on "$service" "converge status | grep -q '^Last sync'"
}

fleet_lists() {
  hub_get /fleet | fleet_has "$@"
}

machine_complete() {
  hub_get "/machine/$1" | machine_has last state
}

bridge_once() {
  compose exec -T hub python3 hub.py bridge-once >> "$LOGS/hub.log" 2>&1
}

hub_checks() {
  check "[phase1] hub /fleet lists linux-a with exit 0" fleet_lists linux-a 0
  check "[phase1] hub /fleet lists linux-b with exit 0" fleet_lists linux-b 0
  check "[phase1] hub bridge-once" bridge_once
  check "[phase1] hub /fleet lists swan-ci after the bridge" fleet_lists swan-ci
  check "[phase1] hub /machine/linux-a has last and state" machine_complete linux-a
  check "[phase1] converge fleet on linux-a lists linux-b" on linux-a "converge fleet | grep -q linux-b"
  check "[phase1] converge fleet --diff on linux-a lists linux-b" on linux-a "converge fleet --diff | grep -q linux-b"
}

stop() {
  compose logs hub >> "$LOGS/hub.log" 2>&1 || true
  if [ "${KEEP:-0}" != 1 ]; then
    compose down --volumes --remove-orphans
  fi
  echo "logs in $LOGS"
}

start
client linux-a linux
client linux-b linux
client swan cluster
hub_checks
stop
finish
