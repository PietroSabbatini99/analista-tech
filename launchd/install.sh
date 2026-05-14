#!/bin/bash
set -e
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

cp "$PROJECT_DIR/launchd/com.analista.tech.plist"       "$LAUNCH_AGENTS/"
cp "$PROJECT_DIR/launchd/com.analista.tech.xscan.plist" "$LAUNCH_AGENTS/"

launchctl load "$LAUNCH_AGENTS/com.analista.tech.plist"
launchctl load "$LAUNCH_AGENTS/com.analista.tech.xscan.plist"

echo "Jobs loaded. Daily 07:00, X scan 08:00-22:00 every 2h."
launchctl list | grep analista
