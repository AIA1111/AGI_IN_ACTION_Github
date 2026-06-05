# HEART BEAT — Self-Recovery Watchdog System

A 24/7 self-maintaining system that keeps all AGI IN ACTION services alive.
If the main app crashes, nginx dies, OpenClaw stops, or any service goes down — the watchdog detects it and auto-restarts everything.

---

## Quick Start (Two Files Only)

| Action | File |
|--------|------|
| **Start everything** | Double-click `HEART_BEAT/START_HEARTBEAT.command` |
| **Kill everything** | Double-click `HEART_BEAT/KILL_HEARTBEAT.command` |

That's it. One click to start, one click to stop.

### What happens when you START:
1. A Terminal window opens briefly — shows confirmation, then you can **close it safely**
2. The watchdog runs silently in background (survives Terminal close via `nohup`)
3. A **macOS launchd job** is automatically installed — watchdog **survives reboots**
4. Watchdog immediately detects the Main App is not running and launches it
5. Main App opens in a new Terminal with the GUI
6. Nginx, TTS, STT, OpenClaw get monitored and restarted if down
7. Every 60 seconds, the watchdog re-checks everything
8. If any service crashes at any point — watchdog restarts it automatically
9. If M3 Ultra reboots — macOS launchd restarts the watchdog → watchdog restarts everything

**Once you double-click START, the system stays alive FOREVER — through app crashes, Terminal closes, and M3 reboots.**

### What happens when you KILL:
1. launchd job is unloaded AND removed (so nothing auto-starts on reboot)
2. Watchdog is killed (so nothing auto-restarts)
3. Nginx is stopped (with sudo cleanup)
4. OpenClaw Gateway is stopped
5. Main App is stopped (which also stops TTS/STT/API server)
6. **Everything is dead. Nothing comes back until you click START again.**

---

## Services Monitored

| Service | Port | Check Type | Auto-Restart | Notes |
|---------|------|------------|--------------|-------|
| Main App (AGI IN ACTION) | — | Process check (`pgrep`) | Yes (watchdog) | Restarted via `.command` file |
| API Server (Flask/Waitress) | 8081 | TCP socket | Yes (child of Main App) | Restart triggers Main App restart |
| Nginx | 443 | PID file | Yes (independent) | Clean stop + start with sudo |
| Kokoro TTS / WebSocket | 8765 | TCP socket | Yes (child of Main App) | Shared with Digital Brain project |
| Whisper STT / HTTP | 8766 | TCP socket | Yes (child of Main App) | Shared with Digital Brain project |
| OpenClaw Gateway | 18789 | TCP socket | Yes (independent) | Uses `openclaw_bridge.start_gateway()` |
| FRP Client (VPS Tunnel) | — | Process check (`pgrep`) | Yes (independent) | Located at `~/FRPC/frpc`, uses `frpc.ini` |

**Key:**
- "Child of Main App" = TTS, STT, API server all start inside the main app process. If any goes down, main app is restarted which brings them all back.
- "Independent" = Nginx and OpenClaw can be restarted without touching the main app.
- Kokoro TTS (8765) and Whisper STT (8766) are **owned by this project** but shared with the Digital Brain project (which only monitors them).

---

## How to Check if Watchdog is Running

### Method 1: Terminal Command
```bash
# Quick check — prints PID if running, nothing if not
cat HEART_BEAT/watchdog_agi.pid 2>/dev/null && echo "Running" || echo "Not running"

# Verify PID is actually alive
kill -0 $(cat HEART_BEAT/watchdog_agi.pid 2>/dev/null) 2>/dev/null && echo "Alive" || echo "Dead"
```

### Method 2: View Live Logs
```bash
tail -f /tmp/heartbeat_watchdog_agi.log
```
This shows the watchdog's health check output in real-time (even though it runs in background).

---

## Safety Features

- **Background Process** — Watchdog runs via `nohup`, survives Terminal close
- **Duplicate Guard** — Before restarting Main App, checks if it's already running (prevents double-launch)
- **Restart Cooldown** — Max 3 restart attempts per service per 10 minutes
- **Smart Skip** — If Main App was just restarted, child services (API, TTS, STT) restart is skipped (they come up with the main app)
- **Single Instance** — Only one watchdog can run at a time (PID file guard)
- **Graceful Shutdown** — SIGTERM first, SIGKILL only after 2 seconds
- **Clean Nginx Restart** — Stops nginx first (with sudo + force kill fallback), cleans temp dirs, then fresh start

---

## Nginx Restart Details

Nginx in this project is complex:
- Runs on privileged port **443** (requires `sudo`)
- Config and PID are written to `/tmp/qr_api_nginx/` (not project folder)
- Managed by `qr_api_linux_module_1.py` (`start_nginx_silently()` / `stop_nginx_silently()`)
- Restart strategy: **clean stop** (sudo nginx -s stop + force kill + temp cleanup) → **2 second wait** → **fresh start** (recreates temp dirs, copies config, starts with sudo)

---

## launchd Auto-Start (Automatic)

The `START_HEARTBEAT.command` **automatically installs** a macOS launchd job that:
- Starts the watchdog on every login/reboot (`RunAtLoad: true`)
- Restarts the watchdog if it crashes (`KeepAlive: true`)
- Throttles restarts to avoid rapid cycling (`ThrottleInterval: 10s`)

The plist file is: `HEART_BEAT/com.agiiinaction.heartbeat.plist`
It gets copied to `~/Library/LaunchAgents/` automatically on START.

The `KILL_HEARTBEAT.command` **automatically removes** the launchd job (unloads + deletes plist) so nothing comes back after kill.

**You don't need to do anything manually** — START installs it, KILL removes it.

---

## File Structure

```
HEART_BEAT/
  __init__.py                          — Module marker
  service_monitor.py                   — Health check engine (TCP, process, PID file checks)
  heartbeat_manager.py                 — GUI facade (embedded mode, monitoring only)
  heartbeat_watchdog.py                — Standalone daemon (the real guardian)
  com.agiiinaction.heartbeat.plist     — macOS launchd job (auto-installed by START)
  watchdog_agi.pid                         — Created at runtime (PID of running watchdog)
  START_HEARTBEAT.command              — Double-click to start everything (installs launchd)
  KILL_HEARTBEAT.command               — Double-click to kill everything (removes launchd)
  README.md                            — This file

Logs:
  /tmp/heartbeat_watchdog_agi.log — Watchdog output (background mode)
```

---

## Adding New Services

Edit `HEART_BEAT/service_monitor.py` and add a new entry to `self.services`:

```python
'my_service': ServiceDefinition(
    name='My Service (9000)',
    key='my_service',
    check_type='tcp',       # 'tcp', 'process', or 'pid_file'
    port=9000,
    can_restart=True,       # False = monitor only
    enabled=True,           # False = placeholder
),
```

Then add a restart strategy in `restart_service()` if `can_restart=True`.

---

**Last Updated:** 2026-02-26
**Adapted from:** Digital Brain project HEART_BEAT system
