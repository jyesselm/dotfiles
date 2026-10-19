# Travel TV kit: Onn 4K Pro setup

Onn 4K Pro (2026, Google TV) for hotel TVs. Plays Plex and the subscriptions in 4K; Tailscale reaches the Plex server
and can send traffic out through home (exit node `plex-server`). Can be done from any Mac on the same Wi-Fi as the Onn.
Tasks app chain: "🧳 Travel TV kit: Onn 4K Pro + Beryl AX router".

## 1. You: basic setup (10 min)

1. Plug the Onn into a TV and power (USB-C). Follow the on-screen setup with the **Google Home** app on your iPhone.
2. Join the home Wi-Fi and sign in to Google.

## 2. You: turn on wireless debugging (2 min)

1. Settings → System → About → click **Android TV OS build** 7 times ("You are now a developer").
2. Settings → System → Developer options → turn on **USB debugging** and **Wireless debugging**.
3. Open **Wireless debugging → Pair device with pairing code**. Leave that screen up; it shows a 6-digit code and an
   `IP:port` for pairing. The main Wireless debugging screen shows a second `IP:port` for connecting.

## 3. On the Mac: connect (Claude can do this part)

```sh
brew install android-platform-tools
adb pair <pairing IP:port> <6-digit code>
adb connect <connect IP:port>
adb devices            # should list the Onn as "device"
```

Approve **Always allow from this computer** if the TV asks.

## 4. Claude: set it up over adb

- Look before acting: `adb exec-out screencap -p > onn.png`; remote keys: `adb shell input keyevent KEYCODE_HOME`
  (DPAD_UP/DOWN/LEFT/RIGHT, DPAD_CENTER, BACK).
- Open each app's Play Store page for the user to click **Install**
  (`adb shell am start -a android.intent.action.VIEW -d 'market://details?id=<package>'`). Confirm package names in
  the store; known ones: Plex `com.plexapp.android`, Tailscale `com.tailscale.ipn`, Netflix `com.netflix.ninja`,
  Prime Video `com.amazon.amazonvideo.livingroom`, Disney+ `com.disney.disneyplus`, Kodi `org.xbmc.kodi`,
  Projectivy Launcher `com.spocky.projengmenu` (clean, ad-free home screen).
- Bloat: list with `adb shell pm list packages`, agree a list with the user, then
  `adb shell pm disable-user --user 0 <package>`. Disable only, never uninstall system packages (reversible with
  `pm enable`).
- Snappier menus: `adb shell settings put global window_animation_scale 0.5` (same for
  `transition_animation_scale`, `animator_duration_scale`).
- Save every command that worked as `onn-setup.sh` next to this file, so a reset Onn is one run.
- Projectivy, by remote (its settings open with
  `adb shell am start -n com.spocky.projengmenu/.ui.sidePanels.settings.SettingsActivity`): Edit categories →
  TV Apps → Grid on, Size XS, Advanced settings → Cards per row 5, Row count 2. Home button goes to Projectivy once
  `onn-setup.sh` has disabled the Google TV launcher; the Onn reboots and wireless debugging must be re-enabled.

## 5. You: sign-ins (Claude never enters passwords)

- Plex, Netflix and the others: each shows a code; approve it on your phone.
- Tailscale: Log in → scan the QR code with your iPhone. Then **Exit Node → plex-server**, check Netflix plays,
  and turn the exit node off again until you travel.
- Plex: Settings → Quality → Remote streaming: "Original" is fine (home upload was 87 Mbps on 2026-10-18).

## At the hotel

Plug in the Beryl AX first and log in to the hotel Wi-Fi from the GL.iNet app; then plug the Onn into the TV.
For Seerr, the dashboard or US-only apps abroad, turn on Tailscale's exit node `plex-server` (on the Onn or the Beryl).
