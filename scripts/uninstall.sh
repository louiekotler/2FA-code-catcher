#!/bin/bash

set -e
set -u

APP_NAME="2FA-code-catcher"
PLIST_NAME="com.louiekotler.${APP_NAME}.plist"
EXECUTABLE_PATH="/usr/local/bin/${APP_NAME}"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}"

echo "Uninstalling ${APP_NAME}..."

# 1. Unload the LaunchAgent if loaded
if launchctl list | grep -q "${PLIST_NAME}"; then
    echo "Stopping LaunchAgent..."
    launchctl unload "${PLIST_DEST}" 2>/dev/null || true
fi

# 2. Kill any remaining processes
echo "Killing any running processes..."
pkill -f "${APP_NAME}" || true

# 3. Remove the LaunchAgent plist
if [ -f "${PLIST_DEST}" ]; then
    echo "Removing plist..."
    rm "${PLIST_DEST}"
fi

# 4. Remove the executable
if [ -f "${EXECUTABLE_PATH}" ]; then
    echo "Removing executable..."
    sudo rm "${EXECUTABLE_PATH}"
fi

# 5. Remove log files
echo "Removing logs..."
rm -f "/tmp/${APP_NAME}.out" "/tmp/${APP_NAME}.err"

echo "✅ ${APP_NAME} uninstalled successfully!"