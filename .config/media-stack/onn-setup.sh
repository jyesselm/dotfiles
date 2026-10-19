#!/bin/sh
# Onn 4K Pro travel-kit setup over adb. See travel-onn.md for pairing first.
# Usage: onn-setup.sh [IP]   (default 192.168.4.77; connect port is discovered via mDNS)
set -eu
IP=${1:-192.168.4.77}
PORT=$(timeout 6 dns-sd -L "$(timeout 6 dns-sd -B _adb-tls-connect._tcp | awk '/Add/{print $NF; exit}')" _adb-tls-connect._tcp \
       | sed -n 's/.*can be reached at [^:]*:\([0-9]*\).*/\1/p' | head -1)
export ANDROID_SERIAL="$IP:${PORT:-5555}"
adb connect "$ANDROID_SERIAL"
adb wait-for-device

store() { adb shell am start -a android.intent.action.VIEW -d "market://details?id=$1"; sleep 6; adb shell input keyevent KEYCODE_DPAD_CENTER; sleep 3; }
installed() { adb shell pm list packages | grep -q "^package:$1$"; }

# Snappier menus
for s in window_animation_scale transition_animation_scale animator_duration_scale; do
  adb shell settings put global "$s" 0.5
done
# Name, judder-free 24 fps playback, and HDR only when the content is HDR (hotel TVs vary)
adb shell settings put global device_name onn-tv
adb shell settings put secure match_content_frame_rate_user_preference 2
adb shell settings put global hdr_conversion_mode 1

# Apps (Play Store page + Install click). Netflix, Prime, Disney+, Hulu, Apple TV, YouTube TV, Max are preinstalled.
for p in com.plexapp.android com.tailscale.ipn com.spocky.projengmenu; do
  installed "$p" || store "$p"
done

# Bloat: disabled, never uninstalled (undo: adb shell pm enable <pkg>)
for p in com.google.android.youtube.tvmusic com.tubitv com.haystack.android com.instagram.airwave \
         com.onn.updatenotification com.onn.tv.setup.customization com.google.android.play.games; do
  adb shell pm disable-user --user 0 "$p"
done

# Projectivy as home: run its wizard once by hand, then disable the Google TV launcher and its setup fallback.
installed com.spocky.projengmenu && for p in com.google.android.apps.tv.launcherx com.google.android.tungsten.setupwraith; do
  adb shell pm disable-user --user 0 "$p"
done
adb shell "cmd package resolve-activity -a android.intent.action.MAIN -c android.intent.category.HOME" | grep packageName | head -1
