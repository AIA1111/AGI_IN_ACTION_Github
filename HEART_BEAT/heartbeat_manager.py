#!/opt/homebrew/bin/python3.11
"""
Heartbeat Manager — GUI Facade
===============================
Facade class for the HEART BEAT tab in API_Server_Training.py.
Mirrors the AudioBridgeManager pattern: simple start/stop/check API.

Runs a daemon thread that periodically checks all services and auto-restarts
failures. Keeps an in-memory log buffer (deque, never written to disk).
"""

import os
import threading
import time
import logging
from collections import deque
from datetime import datetime
from pathlib import Path

from HEART_BEAT.service_monitor import ServiceMonitor

logger = logging.getLogger('HeartbeatManager')


class HeartbeatManager:
    """Embedded heartbeat monitor for the GUI. Dies with the main app."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.monitor = ServiceMonitor(str(self.project_root))

        # Monitoring state
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Configurable interval (seconds): 60–300 (1–5 min)
        self._interval = 60

        # In-memory log buffer — never written to disk
        self._logs: deque[str] = deque(maxlen=500)

        # Restart cooldown: track {service_key: [timestamp, ...]}
        self._restart_history: dict[str, list[float]] = {}
        self._max_restarts = 3
        self._cooldown_window = 600  # 10 minutes

        # Reference to API server for SSE push (set externally)
        self.api_server = None

        logger.info("HeartbeatManager initialized")

    # -----------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------
    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, seconds: int):
        self._interval = max(60, min(300, seconds))

    @property
    def is_running(self) -> bool:
        return self._running

    # -----------------------------------------------------------------
    # Start / Stop
    # -----------------------------------------------------------------
    def start(self) -> tuple[bool, str]:
        """Start the embedded heartbeat monitoring thread."""
        if self._running:
            return False, "Heartbeat is already running"
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        self._log("Heartbeat monitoring STARTED (interval: {}s)".format(self._interval))
        logger.info("Heartbeat monitoring started")
        return True, "Heartbeat started"

    def stop(self) -> tuple[bool, str]:
        """Stop the embedded heartbeat monitoring thread."""
        if not self._running:
            return False, "Heartbeat is not running"
        self._stop_event.set()
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self._log("Heartbeat monitoring STOPPED")
        logger.info("Heartbeat monitoring stopped")
        return True, "Heartbeat stopped"

    def shutdown(self):
        """Cleanup on app exit."""
        if self._running:
            self.stop()
        logger.info("HeartbeatManager shutdown complete")

    # -----------------------------------------------------------------
    # One-shot check (for GUI "Check All Now" button)
    # -----------------------------------------------------------------
    def check_all_services(self) -> dict[str, tuple[str, bool]]:
        """
        Check all enabled services once.
        Returns {key: (display_name, is_alive)}.
        """
        results = {}
        for key, svc in self.monitor.services.items():
            if svc.enabled:
                alive = self.monitor.check_service(svc)
                results[key] = (svc.name, alive)
        return results

    # -----------------------------------------------------------------
    # Watchdog status (standalone watchdog running?)
    # -----------------------------------------------------------------
    def is_watchdog_running(self) -> bool:
        """Check if the standalone watchdog is running via its PID file."""
        pid_file = self.project_root / "HEART_BEAT" / "watchdog_agi.pid"
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            return False

    # -----------------------------------------------------------------
    # Logs
    # -----------------------------------------------------------------
    def get_logs(self) -> str:
        """Return all log entries as a single string."""
        return '\n'.join(self._logs) if self._logs else '(no logs yet)'

    def clear_logs(self):
        """Clear the in-memory log buffer."""
        self._logs.clear()

    def _log(self, message: str):
        """Add a timestamped entry to the in-memory log buffer."""
        ts = datetime.now().strftime('%H:%M:%S')
        self._logs.append(f"[{ts}] {message}")

    # -----------------------------------------------------------------
    # SSE Push
    # -----------------------------------------------------------------
    def _push_sse_notification(self, service_name: str, action: str, success: bool):
        """Send a heartbeat event to Android via the existing SSE system."""
        if not self.api_server:
            return
        try:
            self.api_server._push_notification({
                "type": "heartbeat",
                "service": service_name,
                "action": action,
                "success": success,
            })
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Restart Cooldown
    # -----------------------------------------------------------------
    def _can_restart(self, key: str) -> bool:
        """Check if a service can be restarted (max 3 per 10 min)."""
        now = time.time()
        history = self._restart_history.get(key, [])
        # Prune old entries
        history = [t for t in history if now - t < self._cooldown_window]
        self._restart_history[key] = history
        return len(history) < self._max_restarts

    def _record_restart(self, key: str):
        """Record a restart attempt for cooldown tracking."""
        if key not in self._restart_history:
            self._restart_history[key] = []
        self._restart_history[key].append(time.time())

    # -----------------------------------------------------------------
    # Heartbeat Loop (daemon thread)
    # -----------------------------------------------------------------
    def _heartbeat_loop(self):
        """
        Main monitoring loop. Checks all services, auto-restarts ONLY nginx.

        IMPORTANT: The embedded heartbeat runs INSIDE the main app, so it must
        NEVER try to restart main_app or fastapi (that would launch duplicate
        GUI windows). Only the standalone watchdog can restart the main app.
        Only nginx can be restarted from here since it's an independent process.
        """
        while not self._stop_event.is_set():
            try:
                results = self.monitor.check_all()

                for key, alive in results.items():
                    svc = self.monitor.services[key]
                    status = "UP" if alive else "DOWN"
                    self._log(f"{svc.name}: {status}")

                    if not alive and key in ('nginx', 'openclaw') and svc.can_restart:
                        # Nginx and OpenClaw are independent services the GUI can safely restart
                        # Never restart main_app/api_server/tts/stt from here (would create duplicates)
                        if self._can_restart(key):
                            self._log(f"  -> Attempting restart: {svc.name}")
                            ok, msg = self.monitor.restart_service(key)
                            self._record_restart(key)
                            result_str = "OK" if ok else "FAILED"
                            self._log(f"  -> Restart {result_str}: {msg}")
                            self._push_sse_notification(svc.name, "restart", ok)
                        else:
                            self._log(f"  -> Cooldown active for {svc.name} (max {self._max_restarts} per {self._cooldown_window // 60}min)")
                    elif not alive:
                        self._log(f"  -> {svc.name} is DOWN (standalone watchdog handles restart)")

            except Exception as e:
                self._log(f"ERROR in heartbeat loop: {e}")
                logger.error(f"Heartbeat loop error: {e}", exc_info=True)

            # Sleep in 1-second increments for responsive shutdown
            for _ in range(self._interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
