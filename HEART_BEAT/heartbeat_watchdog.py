#!/opt/homebrew/bin/python3.11
"""
Heartbeat Watchdog — Standalone Daemon
=======================================
Independent Python process that monitors ALL services including the main app.
Survives app crashes. Only stops when manually killed or via KILL_HEARTBEAT.command.

Usage:
    python HEART_BEAT/heartbeat_watchdog.py
    (or double-click START_HEARTBEAT.command)

PID file: HEART_BEAT/watchdog.pid
Logs: stdout only (visible in Terminal when launched via .command)
"""

import os
import sys
import signal
import time
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import HEART_BEAT module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from HEART_BEAT.service_monitor import ServiceMonitor

# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
CHECK_INTERVAL = 60          # seconds between checks
PID_FILE = PROJECT_ROOT / "HEART_BEAT" / "watchdog_agi.pid"
MAX_RESTARTS = 3             # per service
COOLDOWN_WINDOW = 600        # 10 minutes

# -----------------------------------------------------------------
# State
# -----------------------------------------------------------------
running = True
restart_history: dict[str, list[float]] = {}


def log(message: str):
    """Print timestamped log to stdout."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {message}", flush=True)


def signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global running
    sig_name = signal.Signals(signum).name
    log(f"Received {sig_name} — shutting down gracefully...")
    running = False


def write_pid():
    """Write current PID to file."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    log(f"PID {os.getpid()} written to {PID_FILE}")


def remove_pid():
    """Remove PID file on exit."""
    PID_FILE.unlink(missing_ok=True)
    log("PID file removed")


def can_restart(key: str) -> bool:
    """Check restart cooldown (max 3 per 10 min)."""
    now = time.time()
    history = restart_history.get(key, [])
    history = [t for t in history if now - t < COOLDOWN_WINDOW]
    restart_history[key] = history
    return len(history) < MAX_RESTARTS


def record_restart(key: str):
    """Record a restart attempt."""
    if key not in restart_history:
        restart_history[key] = []
    restart_history[key].append(time.time())


def main():
    global running

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Check if already running FIRST (before printing banner — avoids log spam from launchd retries)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            os.kill(old_pid, 0)
            # Silently exit — another instance is already running
            sys.exit(0)
        except (ValueError, OSError):
            # Stale PID file — remove and continue
            PID_FILE.unlink(missing_ok=True)

    log("=" * 60)
    log("HEARTBEAT WATCHDOG — Standalone Daemon")
    log(f"Project root: {PROJECT_ROOT}")
    log(f"Check interval: {CHECK_INTERVAL}s")
    log(f"Restart cooldown: max {MAX_RESTARTS} per {COOLDOWN_WINDOW // 60} min")
    log("=" * 60)

    write_pid()
    monitor = ServiceMonitor(str(PROJECT_ROOT))

    try:
        while running:
            log("--- Health check cycle ---")
            results = monitor.check_all()
            restarted_this_cycle = set()

            for key, alive in results.items():
                svc = monitor.services[key]
                status = "UP" if alive else "DOWN"
                log(f"  {svc.name}: {status}")

                # Skip child service restarts if main_app was just restarted
                # (API server, TTS, STT are child processes — they come up with the main app)
                if key in ('api_server', 'tts_ws', 'stt_http') and 'main_app' in restarted_this_cycle:
                    if not alive:
                        log(f"  -> Skipping {svc.name} (Main App just restarted, child will come up with it)")
                    continue

                if not alive and svc.can_restart:
                    if can_restart(key):
                        log(f"  -> Restarting {svc.name}...")
                        ok, msg = monitor.restart_service(key)
                        record_restart(key)
                        result_str = "OK" if ok else "FAILED"
                        log(f"  -> Restart {result_str}: {msg}")
                        if ok:
                            restarted_this_cycle.add(key)
                    else:
                        log(f"  -> Cooldown active for {svc.name}")
                elif not alive and not svc.can_restart:
                    log(f"  -> {svc.name} is DOWN (monitor-only)")

            # Sleep in 1-second increments for responsive shutdown
            for _ in range(CHECK_INTERVAL):
                if not running:
                    break
                time.sleep(1)

    finally:
        remove_pid()
        log("Watchdog stopped.")


if __name__ == '__main__':
    main()
