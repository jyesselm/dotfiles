#!/bin/sh
# Build Media Menu.app from MediaMenu.swift and load it as a launchd agent (starts at login, no Dock icon).
set -e
cd "$(dirname "$0")"
APP="$HOME/Applications/Media Menu.app"
LABEL=com.yesselman.media-menu
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$APP/Contents/MacOS"
swiftc -O -o "$APP/Contents/MacOS/MediaMenu" MediaMenu.swift
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
	<key>CFBundleName</key><string>Media Menu</string>
	<key>CFBundleIdentifier</key><string>$LABEL</string>
	<key>CFBundleExecutable</key><string>MediaMenu</string>
	<key>CFBundlePackageType</key><string>APPL</string>
	<key>CFBundleShortVersionString</key><string>1.0</string>
	<key>LSUIElement</key><true/>
	<key>LSMinimumSystemVersion</key><string>14.0</string>
</dict></plist>
EOF
codesign --force --sign - "$APP"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed: $APP, agent $LABEL loaded"
