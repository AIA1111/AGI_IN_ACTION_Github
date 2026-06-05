#!/bin/bash
# HEARTBEAT WATCHDOG — Kill Everything
# Double-click to stop the watchdog AND all managed services.
# This is the master kill switch — nothing restarts after this.

cd "$(dirname "$0")"
cd ..

PLIST_LABEL="com.agiiinaction.heartbeat"
HB_PID_FILE="HEART_BEAT/watchdog_agi.pid"
NGINX_PID_FILE="/tmp/qr_api_nginx/logs/nginx.pid"

echo "============================================================"
echo "  KILL HEARTBEAT — Stopping all services"
echo "============================================================"
echo ""

# -----------------------------------------------------------------
# Step 1: Kill the watchdog FIRST (so it doesn't restart anything)
# -----------------------------------------------------------------

# Unload launchd job if installed (prevents macOS from restarting it)
if launchctl list "$PLIST_LABEL" &>/dev/null; then
    echo "[1/6] Unloading launchd job: $PLIST_LABEL"
    launchctl unload ~/Library/LaunchAgents/${PLIST_LABEL}.plist 2>/dev/null
    rm -f ~/Library/LaunchAgents/${PLIST_LABEL}.plist
    echo "      Done (unloaded + removed plist)."
else
    # Remove plist file even if not loaded (cleanup)
    rm -f ~/Library/LaunchAgents/${PLIST_LABEL}.plist 2>/dev/null
    echo "[1/6] launchd job not loaded — cleaned up"
fi

if [ -f "$HB_PID_FILE" ]; then
    HB_PID=$(cat "$HB_PID_FILE")
    echo "[2/6] Stopping Watchdog (PID $HB_PID)..."
    kill "$HB_PID" 2>/dev/null
    # Wait up to 2 seconds for graceful shutdown
    for i in 1 2 3 4; do
        if ! kill -0 "$HB_PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done
    # Force kill if still alive
    if kill -0 "$HB_PID" 2>/dev/null; then
        kill -9 "$HB_PID" 2>/dev/null
        echo "      Force-killed."
    else
        echo "      Stopped gracefully."
    fi
    rm -f "$HB_PID_FILE"
else
    echo "[2/6] Watchdog not running — skipping"
fi

# -----------------------------------------------------------------
# Step 2: Stop Nginx (uses sudo since port 443)
# -----------------------------------------------------------------
echo "[3/6] Stopping Nginx..."
sudo -n nginx -s stop 2>/dev/null
sleep 1
# Force kill if still alive
if pgrep nginx &>/dev/null; then
    sudo -n pkill -f nginx 2>/dev/null
    echo "      Force-killed."
else
    echo "      Stopped."
fi
# Clean up nginx temp files
rm -rf /tmp/qr_api_nginx 2>/dev/null

# -----------------------------------------------------------------
# Step 3: Stop OpenClaw Gateway (port 18789)
# -----------------------------------------------------------------
OC_PIDS=$(lsof -tiTCP:18789 -sTCP:LISTEN 2>/dev/null)
if [ -n "$OC_PIDS" ]; then
    echo "[4/6] Stopping OpenClaw Gateway (PIDs: $OC_PIDS)..."
    echo "$OC_PIDS" | xargs kill 2>/dev/null
    sleep 1
    REMAINING=$(lsof -tiTCP:18789 -sTCP:LISTEN 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "$REMAINING" | xargs kill -9 2>/dev/null
        echo "      Force-killed."
    else
        echo "      Stopped."
    fi
else
    echo "[4/6] OpenClaw Gateway not running — skipping"
fi

# -----------------------------------------------------------------
# Step 4: Kill FRP Client
# -----------------------------------------------------------------
FRP_PIDS=$(pgrep -f "frpc" 2>/dev/null)
if [ -n "$FRP_PIDS" ]; then
    echo "[5/6] Stopping FRP Client (PIDs: $FRP_PIDS)..."
    echo "$FRP_PIDS" | xargs kill 2>/dev/null
    sleep 1
    REMAINING=$(pgrep -f "frpc" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "$REMAINING" | xargs kill -9 2>/dev/null
        echo "      Force-killed."
    else
        echo "      Stopped."
    fi
else
    echo "[5/6] FRP Client not running — skipping"
fi

# -----------------------------------------------------------------
# Step 5: Kill the Main App (AGI IN ACTION(BASIC) 2.3.py)
# -----------------------------------------------------------------
MAIN_PIDS=$(pgrep -f "AGI IN ACTION" 2>/dev/null)
if [ -n "$MAIN_PIDS" ]; then
    echo "[6/6] Stopping Main App (PIDs: $MAIN_PIDS)..."
    echo "$MAIN_PIDS" | xargs kill 2>/dev/null
    sleep 2
    # Force kill any survivors
    REMAINING=$(pgrep -f "AGI IN ACTION" 2>/dev/null)
    if [ -n "$REMAINING" ]; then
        echo "$REMAINING" | xargs kill -9 2>/dev/null
        echo "      Force-killed remaining processes."
    else
        echo "      Stopped."
    fi
else
    echo "[5/5] Main App not running — skipping"
fi

echo ""
echo "============================================================"
echo "  All services stopped. Nothing will auto-restart."
echo "============================================================"
echo ""
echo "Press any key to close..."
read -n 1
