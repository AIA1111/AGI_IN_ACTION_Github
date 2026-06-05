#!/bin/bash
# ============================================================
# START HEARTBEAT — Launch Watchdog + All Services (FOREVER)
# ============================================================
# Double-click this file to start the self-recovery system.
# The watchdog will:
#   1. Install a macOS launchd job (starts watchdog immediately)
#   2. Auto-restart all services if they crash
#   3. Survive reboots (launchd RunAtLoad + KeepAlive)
#   4. NEVER stop unless you double-click KILL_HEARTBEAT.command
#
# Logs: /tmp/heartbeat_watchdog_agi.log
# ============================================================

cd "$(dirname "$0")"
cd ..

PID_FILE="HEART_BEAT/watchdog_agi.pid"
LOG_FILE="/tmp/heartbeat_watchdog_agi.log"
PLIST_SRC="HEART_BEAT/com.agiiinaction.heartbeat.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agiiinaction.heartbeat.plist"
PLIST_LABEL="com.agiiinaction.heartbeat"

# ----------------------------------------------------------
# Check if already running
# ----------------------------------------------------------
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo ""
        echo "  Heartbeat watchdog is ALREADY RUNNING (PID $OLD_PID)"
        echo ""
        echo "  Logs:  tail -f $LOG_FILE"
        echo "  Stop:  Double-click HEART_BEAT/KILL_HEARTBEAT.command"
        echo ""
        echo "Press any key to close..."
        read -n 1
        exit 0
    else
        echo "Removing stale PID file..."
        rm -f "$PID_FILE"
    fi
fi

echo ""
echo "============================================================"
echo "  STARTING HEARTBEAT WATCHDOG"
echo "  Project: AGI IN ACTION"
echo "============================================================"
echo ""

# ----------------------------------------------------------
# Install launchd job (this IS the launcher — no nohup needed)
# launchd starts the watchdog immediately and keeps it alive
# ----------------------------------------------------------
echo "  Installing launchd job..."

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Unload old version if exists (ignore errors)
launchctl unload "$PLIST_DEST" 2>/dev/null
sleep 1

# Copy plist to LaunchAgents
cp "$PLIST_SRC" "$PLIST_DEST"

# Load the new job — launchd starts watchdog immediately (RunAtLoad: true)
launchctl load "$PLIST_DEST"

# Wait for launchd to start the watchdog
sleep 3

if [ -f "$PID_FILE" ]; then
    WATCHDOG_PID=$(cat "$PID_FILE")
    if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        echo "  Watchdog started successfully via launchd!"
        echo ""
        echo "  PID:   $WATCHDOG_PID"
        echo "  Logs:  tail -f $LOG_FILE"
        echo "  Stop:  Double-click HEART_BEAT/KILL_HEARTBEAT.command"
    else
        echo "  WARNING: PID file exists but process not running."
        echo "  Check logs: $LOG_FILE"
    fi
else
    # launchd may still be starting — check with launchctl
    if launchctl list "$PLIST_LABEL" &>/dev/null; then
        echo "  launchd job loaded — watchdog should start momentarily."
        echo "  Check logs: tail -f $LOG_FILE"
    else
        echo "  FAILED: launchd job did not load."
        echo "  Try manually: launchctl load $PLIST_DEST"
        echo ""
        echo "Press any key to close..."
        read -n 1
        exit 1
    fi
fi

echo ""
echo "  The watchdog will now:"
echo "    1. Monitor all services every 60 seconds"
echo "    2. Auto-restart anything that crashes"
echo "    3. Survive Terminal close (launchd manages it)"
echo "    4. Survive M3 reboot (launchd RunAtLoad)"
echo "    5. NEVER stop until you run KILL_HEARTBEAT.command"
echo ""
echo "  Services monitored:"
echo "    - Main App (AGI IN ACTION)"
echo "    - API Server (8081)"
echo "    - Nginx (443)"
echo "    - Kokoro TTS / WebSocket (8765)"
echo "    - Whisper STT / HTTP (8766)"
echo "    - OpenClaw Gateway (18789)"
echo "    - FRP Client (VPS Tunnel — ~/FRPC/)"
echo ""
echo "  You can SAFELY CLOSE this Terminal window."
echo ""

echo "Press any key to close..."
read -n 1
