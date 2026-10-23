#!/bin/bash
# QV9 Lid Handler fallback v0.2
set -euo pipefail

POWER="org.cinnamon.settings-daemon.plugins.power"

if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
    XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi

LOCK="$XDG_RUNTIME_DIR/qv9-lid-owner.lock"

# Serialize restoration with the login safety script.
exec 9>"$LOCK"

if ! flock -w 5 9; then
    logger -t qv9-lid-fallback         "ERROR: Ownership lock unavailable"
    exit 1
fi

gsettings set "$POWER" lid-close-ac-action suspend
gsettings set "$POWER" lid-close-battery-action suspend

AC=$(gsettings get "$POWER" lid-close-ac-action)
BAT=$(gsettings get "$POWER" lid-close-battery-action)

if [[ "$AC" != "'suspend'" || "$BAT" != "'suspend'" ]]; then
    logger -t qv9-lid-fallback         "ERROR: Cinnamon lid policy verification failed"
    exit 1
fi

logger -t qv9-lid-fallback     "Fallback v0.2: Cinnamon lid actions restored"

echo "QV9 fallback v0.2: Cinnamon lid actions restored"
