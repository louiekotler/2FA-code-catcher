
#!/bin/bash

set -e  # stop on first error
set -u  # treat unset variables as errors

APP_NAME="2FA-code-catcher"
PLIST_NAME="com.louiekotler.${APP_NAME}.plist"
EXECUTABLE_PATH="/usr/local/bin/${APP_NAME}"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}"

echo "Installing ${APP_NAME}..."

# 1. Copy the executable
if [ ! -f "../dist/${APP_NAME}" ]; then
    echo "❌ Executable not found at ../dist/${APP_NAME}"
    exit 1
fi

echo "Copying executable to ${EXECUTABLE_PATH}..."
sudo cp "../dist/${APP_NAME}" "${EXECUTABLE_PATH}"
sudo chmod 755 "${EXECUTABLE_PATH}"

# 2. Copy the LaunchAgent plist
if [ ! -f "../launchd/${PLIST_NAME}" ]; then
    echo "❌ Plist not found at ../launchd/${PLIST_NAME}"
    exit 1
fi

echo "Copying LaunchAgent to ${PLIST_DEST}..."
cp "../launchd/${PLIST_NAME}" "${PLIST_DEST}"
chmod 644 "${PLIST_DEST}"

# 3. Unload if already loaded (ignore errors)
launchctl unload "${PLIST_DEST}" 2>/dev/null || true

# 4. Load the plist under the current user
echo "Loading LaunchAgent..."
launchctl load "${PLIST_DEST}"

echo "✅ Installed and started ${APP_NAME}!"
echo "Logs: /tmp/${APP_NAME}.out and /tmp/${APP_NAME}.err"
