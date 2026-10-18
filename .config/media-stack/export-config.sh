#!/usr/bin/env bash
# Dump each app's settings to app-config/ as JSON, with secrets stripped, so they can be tracked in dotfiles.
# Reference for rebuilding from scratch; a normal move copies $DATA_ROOT instead (README.md).
# Indexers are left out on purpose (public repo). Needs curl + jq; works on macOS and Linux.
set -euo pipefail
cd "$(dirname "$0")"
out=app-config
env_val() { sed -n "s/^$1=//p" .env; }
secret='key|token|secret|pass|vapid|clientid|webhook|cookie|auth'

# Drop secret-looking keys anywhere, and blank *arr "fields" entries that are private or secret-named.
clean() {
  jq --arg re "$secret" 'walk(
    if type == "object" then
      with_entries(select(.key | test($re; "i") | not))
      | if (.name? | type) == "string" and has("value")
           and ((.privacy? // "normal") != "normal" or (.name | test($re; "i")))
        then .value = "" else . end
    else . end)'
}

dump() {  # app port api-version key endpoint...
  local app=$1 port=$2 ver=$3 key=$4; shift 4
  mkdir -p "$out/$app"
  for ep in "$@"; do
    curl -fsS -H "X-Api-Key: $key" "http://localhost:$port/api/$ver/$ep" | clean >"$out/$app/${ep//\//-}.json"
  done
}

arr=(customformat qualityprofile delayprofile tag rootfolder downloadclient remotepathmapping
     config/naming config/mediamanagement config/downloadclient)
dump radarr 7878 v3 "$(env_val HOMEPAGE_VAR_RADARR_KEY)" "${arr[@]}"
dump sonarr 8989 v3 "$(env_val HOMEPAGE_VAR_SONARR_KEY)" "${arr[@]}"
dump prowlarr 9696 v1 "$(env_val HOMEPAGE_VAR_PROWLARR_KEY)" applications appprofile tag
mkdir -p "$out/seerr"
clean <"$(env_val DATA_ROOT)/seerr/config/settings.json" >"$out/seerr/settings.json"
echo "Wrote $out/. Check 'git diff' before committing."
