#!/opt/homebrew/bin/python3.11
"""
Service Monitor — Health Check & Restart Engine
================================================
Core engine for checking service health and restarting failed services.
Adapted for AGI IN ACTION project (2026-02-26).

Services monitored:
  - Main App (AGI IN ACTION(BASIC) 2.3.py) — process check
  - API Server / Flask+Waitress (8081) — TCP check, child of main app
  - Nginx (443) — PID file check, can restart independently
  - Kokoro TTS / WebSocket (8765) — TCP check, child of main app
  - Whisper STT / HTTP (8766) — TCP check, child of main app
  - OpenClaw Gateway (18789) — TCP check, can restart independently
  - FRP Client — placeholder (enabled=False)
"""

import os
import socket
import subprocess
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger('ServiceMonitor')


@dataclass
class ServiceDefinition:
    """Definition of a monitored service."""
    name: str
    key: str
    check_type: str  # 'tcp', 'process', 'pid_file'
    enabled: bool = True
    port: int = 0
    process_name: str = ''
    pid_file: str = ''
    restart_command: str = ''
    can_restart: bool = False  # False = monitor-only


class ServiceMonitor:
    """Health check and restart engine for AGI IN ACTION services."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        # Nginx PID is written to /tmp by qr_api_linux_module_1.py start_nginx_silently()
        self.nginx_pid_path = Path("/tmp/qr_api_nginx/logs/nginx.pid")
        self.command_file = self.project_root / "launch_with_terminal.command_AGI_IN_ACTION.command"

        # Define all services
        self.services: dict[str, ServiceDefinition] = {
            'main_app': ServiceDefinition(
                name='Main App (AGI IN ACTION)',
                key='main_app',
                check_type='process',
                process_name='AGI IN ACTION',  # No parentheses — pgrep treats () as regex
                restart_command=str(self.command_file),
                can_restart=True,
            ),
            'api_server': ServiceDefinition(
                name='API Server (8081)',
                key='api_server',
                check_type='tcp',
                port=8081,
                # API Server is a child of main app — restart main app if down
                restart_command=str(self.command_file),
                can_restart=True,
            ),
            'nginx': ServiceDefinition(
                name='Nginx (443)',
                key='nginx',
                check_type='pid_file',
                port=443,
                pid_file=str(self.nginx_pid_path),
                can_restart=False,  # Monitor-only — requires sudo, watchdog daemon can't restart
            ),
            'tts_ws': ServiceDefinition(
                name='Kokoro TTS / WebSocket (8765)',
                key='tts_ws',
                check_type='tcp',
                port=8765,
                # TTS/WebSocket is a child of main app — restart main app if down
                can_restart=True,
            ),
            'stt_http': ServiceDefinition(
                name='Whisper STT / HTTP (8766)',
                key='stt_http',
                check_type='tcp',
                port=8766,
                # STT/HTTP is a child of main app — restart main app if down
                can_restart=True,
            ),
            'openclaw': ServiceDefinition(
                name='OpenClaw Gateway (18789)',
                key='openclaw',
                check_type='tcp',
                port=18789,
                can_restart=True,
            ),
            'frp_client': ServiceDefinition(
                name='FRP Client (VPS Tunnel)',
                key='frp_client',
                check_type='process',
                process_name='frpc',
                can_restart=True,
            ),
        }

    # -----------------------------------------------------------------
    # Health Checks
    # -----------------------------------------------------------------
    def check_tcp(self, port: int, host: str = '127.0.0.1',
                  timeout: float = 1.0) -> bool:
        """Check whether a TCP service is accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False

    def check_process(self, name: str) -> bool:
        """Check whether a process matching `name` is running (pgrep -f)."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', name],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_pid_file(self, path: str) -> bool:
        """Check PID file exists and process is alive (os.kill(pid, 0))."""
        pid_path = Path(path)
        if not pid_path.exists():
            return False
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            return False

    def check_service(self, svc: ServiceDefinition) -> bool:
        """Run the appropriate health check for a service."""
        if not svc.enabled:
            return False
        if svc.check_type == 'tcp':
            return self.check_tcp(svc.port)
        elif svc.check_type == 'process':
            return self.check_process(svc.process_name)
        elif svc.check_type == 'pid_file':
            return self.check_pid_file(svc.pid_file)
        return False

    def check_all(self) -> dict[str, bool]:
        """Check all enabled services. Returns {key: is_alive}."""
        results = {}
        for key, svc in self.services.items():
            if svc.enabled:
                results[key] = self.check_service(svc)
        return results

    # -----------------------------------------------------------------
    # Restart Logic
    # -----------------------------------------------------------------
    def restart_service(self, key: str) -> tuple[bool, str]:
        """Attempt to restart a service. Returns (success, message)."""
        svc = self.services.get(key)
        if not svc:
            return False, f"Unknown service: {key}"
        if not svc.enabled:
            return False, f"{svc.name} is disabled"
        if not svc.can_restart:
            return False, f"{svc.name} is monitor-only"

        # Nginx restarts independently
        if key == 'nginx':
            return self._restart_nginx()

        # OpenClaw restarts independently
        if key == 'openclaw':
            return self._restart_openclaw()

        # FRP Client restarts independently
        if key == 'frp_client':
            return self._restart_frpc()

        # Main app, API server, TTS, STT — all children of main app
        if key in ('main_app', 'api_server', 'tts_ws', 'stt_http'):
            return self._restart_main_app()

        return False, f"No restart strategy for {svc.name}"

    def _restart_nginx(self) -> tuple[bool, str]:
        """Restart nginx — monitor only from watchdog.

        Nginx requires sudo for port 443 and the watchdog daemon (launchd)
        does not have sudo access. Attempting to restart from here would
        force-kill any running nginx and then fail to start a new one.
        The Main App GUI handles nginx start/stop (it has sudo from Terminal).
        """
        # The watchdog cannot restart nginx (sudo required, not available in daemon).
        # Log and skip — the user must restart nginx from the GUI "Start Servers" button.
        logger.warning("Nginx is DOWN — watchdog cannot restart (sudo required). Use GUI 'Start Servers' button.")
        return False, "Nginx requires sudo — restart from GUI 'Start Servers' button"

    def _restart_openclaw(self) -> tuple[bool, str]:
        """Restart OpenClaw gateway using openclaw_bridge module."""
        try:
            import sys
            sys.path.insert(0, str(self.project_root))
            from OpenClaw.openclaw_bridge import start_gateway
            ok, msg = start_gateway()
            if ok:
                logger.info(f"OpenClaw restarted: {msg}")
                return True, f"OpenClaw restarted: {msg}"
            else:
                logger.error(f"OpenClaw restart failed: {msg}")
                return False, f"OpenClaw restart failed: {msg}"
        except Exception as e:
            logger.error(f"OpenClaw restart error: {e}")
            return False, str(e)

    def _restart_frpc(self) -> tuple[bool, str]:
        """Restart FRP client (located in ~/FRPC/, independent of this project)."""
        frpc_dir = Path.home() / "FRPC"
        frpc_bin = frpc_dir / "frpc"
        frpc_config = frpc_dir / "frpc.ini"

        if not frpc_bin.exists():
            return False, f"frpc binary not found at {frpc_bin}"
        if not frpc_config.exists():
            return False, f"frpc.ini not found at {frpc_config}"

        # Kill any existing frpc process first
        try:
            subprocess.run(['pkill', '-f', 'frpc'], capture_output=True, timeout=5)
            import time
            time.sleep(1)
        except Exception:
            pass

        try:
            # Start frpc in background with nohup (survives parent exit)
            subprocess.Popen(
                ['nohup', str(frpc_bin), '-c', str(frpc_config)],
                cwd=str(frpc_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            import time
            time.sleep(2)

            # Verify it started
            if self.check_process('frpc'):
                logger.info("FRP client restarted successfully")
                return True, "FRP client restarted"
            else:
                return False, "FRP client started but process not detected"
        except Exception as e:
            logger.error(f"FRP client restart error: {e}")
            return False, str(e)

    def _restart_main_app(self) -> tuple[bool, str]:
        """Restart the main app by opening the .command file in a new Terminal."""
        import time

        # Guard: don't launch if already running (prevents duplicate GUI windows)
        if self.check_process('AGI IN ACTION'):
            return False, "Main App process already running — skipping restart"

        if not self.command_file.exists():
            return False, f"Launch file not found: {self.command_file}"

        # Kill any zombie/hung instances first (clean slate)
        try:
            subprocess.run(
                ['pkill', '-f', 'AGI IN ACTION'],
                capture_output=True, timeout=5
            )
            time.sleep(2)
        except Exception:
            pass

        # Double-check it's really dead before launching
        if self.check_process('AGI IN ACTION'):
            return False, "Main App still running after kill attempt — skipping restart"

        try:
            subprocess.Popen(['open', str(self.command_file)])
            logger.info(f"Main app restart triggered via: {self.command_file.name}")
            return True, "Main app restart triggered (new Terminal window)"
        except Exception as e:
            logger.error(f"Main app restart error: {e}")
            return False, str(e)
