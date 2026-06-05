"""
Enhanced WebSocket Client for TTS/STT with Auto-Connect and Stability Features
Handles Kokoro TTS and Whisper STT requests to M3 server
"""

import asyncio
import json
import logging
import threading
import time
import numpy as np
import websockets
import base64
import soundfile as sf
from typing import Dict, Any, Optional, Callable
import os
###HTTP Client imports
import requests
import os

class WebSocketClient_TTSAndSTT:
    def __init__(self, host: str = 'localhost', port: int = 8765):
        # Initialize client_id FIRST to avoid attribute errors
        import uuid
        try:
            self.client_id = str(uuid.uuid4())[:8]  # Short unique ID for diagnostics
        except Exception:
            self.client_id = "unknown"  # Fallback if UUID generation fails

        # Connection settings - these must come before any logging
        self.host = host
        self.port = port
        self.websocket_url = f"ws://{host}:{port}"
        self.http_port = 8766  # HTTP server port for large file downloads

        # Initialize all basic attributes before any method calls
        self.websocket = None
        self.connected = False
        self.connecting = False
        self.should_reconnect = True

        # Threading attributes
        self.loop = None
        self.thread = None
        self.running = False

        # Health monitoring attributes - initialize before logger setup
        self.auto_connect_enabled = False
        self.health_check_timer = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 60  # seconds

        # Heartbeat attributes
        self.last_ping_time = 0
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None

        # Config and response handling
        self.config_file = "websocket_config.json"
        self.pending_requests = {}
        self.request_id_counter = 0

        # Callbacks for GUI updates
        self.status_callback = None
        self.log_callback = None

        # NOW it's safe to initialize the logger (which might use client_id)
        self.logger = self._setup_logger()

        # Add diagnostic logging AFTER logger is initialized
        self.logger.debug(f"[DIAGNOSTIC] WebSocket client instance created with ID: {self.client_id}")
        self.logger.debug(f"[DIAGNOSTIC] Target connection: {self.websocket_url}")

        # Load config but control auto-connect behavior
        try:
            self.load_config()

            # Only auto-connect if enabled and not overridden
            if self.auto_connect_enabled:
                self.logger.info(f"[DIAGNOSTIC] Auto-connecting client {self.client_id}")
                self.start_client()
            else:
                self.logger.info(f"[DIAGNOSTIC] Auto-connect disabled for client {self.client_id}")

        except Exception as e:
            self.logger.error(f"[DIAGNOSTIC] Initialization error: {e}")

    def _get_protocol(self):
        """Unwrap protocol from ClientConnection if needed"""
        if self.websocket is None:
            return None
        # Some versions of websockets return ClientConnection with .protocol
        return getattr(self.websocket, "protocol", self.websocket)

    def _setup_logger(self) -> logging.Logger:
        """Setup Windows-compatible logger with comprehensive diagnostics"""
        logger = logging.getLogger('WebSocketClient')
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create file handler for persistent debugging - UTF-8 encoding
        file_handler = logging.FileHandler('websocket_client_detailed.log', mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Create console handler for real-time monitoring - Windows compatible
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Windows-compatible formatter without emoji characters
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _log_connection_state(self, event: str, additional_info: str = ""):
        """Log detailed connection state for diagnostics - Windows compatible"""
        state_summary = {
            'connected': self.connected,
            'connecting': self.connecting,
            'pending_requests': len(self.pending_requests),
            'reconnect_attempts': self.reconnect_attempts,
            'should_reconnect': self.should_reconnect,
            'running': self.running
        }

        message = f"[CONNECTION] {event} - {additional_info} | State: {state_summary}"
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def set_callbacks(self, status_callback: Callable = None, log_callback: Callable = None):
        """Set callbacks for GUI updates"""
        self.status_callback = status_callback
        self.log_callback = log_callback

    def _update_status(self, status: str, color: str = 'black'):
        """Update GUI status"""
        if self.status_callback:
            self.status_callback(status, color)

    def _log_message(self, message: str):
        """Log message to GUI and logger"""
        timestamp = time.strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}"
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(formatted_msg)

    def save_config(self, host: str = None, port: int = None, auto_connect: bool = None):
        """Save WebSocket configuration to file with robust error handling"""
        try:
            # Ensure client_id exists for diagnostic logging
            client_id = getattr(self, 'client_id', 'temp_config_client')

            # Load existing config
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

            # Update with new values
            if host is not None:
                config['host'] = host
                self.host = host
            if port is not None:
                config['port'] = port
                self.port = port
            if auto_connect is not None:
                config['auto_connect_enabled'] = auto_connect
                self.auto_connect_enabled = auto_connect

            self.websocket_url = f"ws://{self.host}:{self.port}"

            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Safe logging that works even if logger isn't initialized
            log_message = f"[DIAGNOSTIC] Client {client_id} - Config saved: {self.host}:{self.port}, Auto-connect: {self.auto_connect_enabled}"
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(log_message)
            else:
                print(log_message)  # Fallback if logger not available

            return True
        except Exception as e:
            error_message = f"[DIAGNOSTIC] Config save error: {e}"
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)  # Fallback logging
            return False

    def load_config(self):
        """Load WebSocket configuration from file with robust error handling"""
        try:
            client_id = getattr(self, 'client_id', 'config_loader')

            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.host = config.get('host', self.host)
                    self.port = config.get('port', self.port)
                    self.auto_connect_enabled = config.get('auto_connect_enabled', False)
                    self.websocket_url = f"ws://{self.host}:{self.port}"

                    # Safe logging
                    log_message = f"[DIAGNOSTIC] Client {client_id} - Config loaded: {self.host}:{self.port}, Auto-connect: {self.auto_connect_enabled}"
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.info(log_message)
                    else:
                        print(log_message)

        except Exception as e:
            error_message = f"[DIAGNOSTIC] Config load error: {e}"
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(error_message)
            else:
                print(error_message)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'host': self.host,
            'port': self.port,
            'auto_connect_enabled': self.auto_connect_enabled
        }

    def start_client(self) -> bool:
        """Start WebSocket client with auto-connect support"""
        if self.running:
            self._log_message("Client already running")
            return True

        try:
            self.should_reconnect = True
            self.running = True
            self.thread = threading.Thread(target=self._run_client, daemon=True)
            self.thread.start()

            # Wait a moment to establish connection
            time.sleep(2)

            # Start health check timer
            self._start_health_check()

            return self.connected
        except Exception as e:
            self._log_message(f"Start client error: {e}")
            return False

    def stop_client(self):
        """Stop WebSocket client"""
        self.should_reconnect = False
        self.running = False

        # Stop health check
        self._stop_health_check()

        # Close connection
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._close_connection(), self.loop)

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.connected = False
        self._update_status("Disconnected", 'red')
        self._log_message("Client stopped")

    def _run_client(self):
        """Run WebSocket client in separate thread"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._client_loop())
        except Exception as e:
            self._log_message(f"Client loop error: {e}")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _client_loop(self):
        """Main client connection loop with reconnection logic"""
        while self.running and self.should_reconnect:
            try:
                await self._connect_websocket()
                self.reconnect_attempts = 0  # Reset on successful connection

                # Keep connection alive
                await self._maintain_connection()

            except Exception as e:
                self._log_message(f"Connection error: {e}")

            # Reconnection logic
            if self.should_reconnect and self.running:
                await self._handle_reconnection()

    async def _connect_websocket(self):
        """Establish WebSocket connection with enhanced diagnostics"""
        if self.connecting:
            self.logger.warning(
                f"[DIAGNOSTIC] Client {getattr(self, 'client_id', 'unknown')} already connecting, skipping duplicate attempt")
            return

        self.connecting = True
        try:
            # Track connection attempts safely
            if not hasattr(self, 'connection_attempt_count'):
                self.connection_attempt_count = 0
            self.connection_attempt_count += 1

            self.logger.info(
                f"[DIAGNOSTIC] Client {getattr(self, 'client_id', 'unknown')} starting connection attempt #{self.connection_attempt_count} to {self.websocket_url}")

            self._log_message(f"Connecting to {self.websocket_url}")
            self._update_status("Connecting...", 'orange')

            # Your existing websocket connection code continues here
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=None,  # We'll handle our own heartbeat
                ping_timeout=None,
                close_timeout=10
            )

            self.connected = True
            self.connecting = False
            self._update_status("Connected", 'green')
            self._log_message(f"Connected to {self.host}:{self.port}")

            self.logger.info(f"[DIAGNOSTIC] Client {getattr(self, 'client_id', 'unknown')} successfully connected")

            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except Exception as e:
            self.connected = False
            self.connecting = False
            self._update_status("Connection Failed", 'red')
            self.logger.error(f"[DIAGNOSTIC] Client {getattr(self, 'client_id', 'unknown')} connection failed: {e}")
            raise e

    async def _maintain_connection(self):
        """Maintain WebSocket connection and route responses"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'pong':
                        self.last_ping_time = time.time()
                    elif message_type in ['tts_response', 'stt_response']:
                        # Route response to waiting request
                        request_id = data.get('request_id')
                        if request_id and request_id in self.pending_requests:
                            future = self.pending_requests[request_id]
                            if not future.done():
                                future.set_result(data)

                except json.JSONDecodeError:
                    pass  # Ignore non-JSON messages

        except websockets.exceptions.ConnectionClosed:
            self._log_message("Connection closed by server")
            self.connected = False
            self._update_status("Disconnected", 'red')
        except Exception as e:
            self._log_message(f"Connection maintenance error: {e}")
            self.connected = False

    async def _handle_reconnection(self):
        """Handle reconnection with exponential backoff"""
        if not self.should_reconnect or not self.running:
            return

        self.reconnect_attempts += 1
        if self.reconnect_attempts > self.max_reconnect_attempts:
            self._log_message("Max reconnection attempts reached")
            self.should_reconnect = False
            return

        # Exponential backoff
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )

        self._log_message(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts})")
        self._update_status(f"Reconnecting in {delay}s", 'orange')

        await asyncio.sleep(delay)

    async def _heartbeat_loop(self):
        """Send periodic heartbeat pings"""
        try:
            proto = self._get_protocol()
            while self.connected and proto and getattr(proto, "open", False):
                try:
                    ping_message = json.dumps({'type': 'ping', 'timestamp': time.time()})
                    await self.websocket.send(ping_message)
                    self.last_ping_time = time.time()
                    await asyncio.sleep(self.heartbeat_interval)
                except Exception as e:
                    self._log_message(f"Heartbeat error: {e}")
                    break
        except asyncio.CancelledError:
            pass

    async def _close_connection(self):
        """Close WebSocket connection"""
        try:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            proto = self._get_protocol()
            if proto and getattr(proto, "open", False):
                await proto.close()

        except Exception as e:
            self._log_message(f"Close connection error: {e}")

    def _intelligent_health_check(self):
        """Perform smart health check with proper timer management"""
        try:
            self.logger.info("[HEALTH] Health check starting...")

            # Don't check if we're not supposed to be running
            if not self.running:
                self.logger.info("[HEALTH] Health check: Client not running, skipping")
                return

            # Prevent overlapping health checks during reconnection
            if self.connecting:
                self.logger.info("[HEALTH] Health check: Currently connecting, skipping this check")
                # Still schedule next check even if we skip this one
                self._schedule_next_health_check()
                return

            # Detailed connection assessment with improved logic
            connection_assessment = self._assess_connection_health_improved()

            if connection_assessment['is_healthy']:
                # This is the log message you want to see every minute when connection is stable
                self.logger.info(f"[HEALTH] *** CONNECTION STABLE *** - {connection_assessment['reason']}")

                # Test server communication with actual ping
                ping_success = self._test_server_ping()
                if ping_success:
                    self.logger.info("[HEALTH] Server ping test PASSED - Communication verified")
                else:
                    self.logger.warning("[HEALTH] Server ping test FAILED - but connection appears stable")

                # Schedule next health check after successful check
                self._schedule_next_health_check()

            else:
                self.logger.warning(f"[HEALTH] CONNECTION UNHEALTHY - {connection_assessment['reason']}")
                self.logger.info("[HEALTH] Initiating connection restart due to genuine health issue")

                # Don't schedule next health check - restart will handle it
                if self.loop and not self.loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self._restart_connection(), self.loop)

        except Exception as e:
            self.logger.error(f"[HEALTH] Health check error: {e}")
            # Even if there's an error, schedule the next check
            self._schedule_next_health_check()

    def _schedule_next_health_check(self):
        """Schedule the next health check with proper timer cleanup"""
        if not self.running:
            return

        # CRITICAL: Stop any existing health check timer before starting new one
        self._stop_health_check()

        # Set the interval (60 seconds for testing, change to 3600 for 1 hour later)
        check_interval = 3600  # 3600 seconds

        self.logger.debug(f"[HEALTH] Scheduling next health check in {check_interval} seconds")

        # Start new timer
        self.health_check_timer = threading.Timer(check_interval, self._intelligent_health_check)
        self.health_check_timer.daemon = True
        self.health_check_timer.start()

    def _start_health_check(self):
        """Start health monitoring - used only for initial startup"""
        # This should only be called once during client startup
        if not self.running:
            return

        check_interval = 60  # 60 seconds
        self.logger.info(f"[HEALTH] Starting initial health monitoring with {check_interval}s interval")

        # Ensure no existing timer
        self._stop_health_check()

        # Start the first health check timer
        self.health_check_timer = threading.Timer(check_interval, self._intelligent_health_check)
        self.health_check_timer.daemon = True
        self.health_check_timer.start()

    def _assess_connection_health_improved(self) -> dict:
        """Improved connection health assessment that reduces false positives"""

        # Check 1: Are we supposed to be connected?
        if not self.connected:
            return {
                'is_healthy': False,
                'reason': 'Client reports disconnected state'
            }

        # Check 2: Is the websocket object valid?
        if not self.websocket:
            return {
                'is_healthy': False,
                'reason': 'WebSocket object is None'
            }

        # Check 3: Try a more reliable way to check connection status
        try:
            # Instead of checking protocol.open, let's check if websocket is still active
            # by looking at its state more carefully
            if hasattr(self.websocket, 'closed'):
                if self.websocket.closed:
                    return {
                        'is_healthy': False,
                        'reason': 'WebSocket reports closed state'
                    }

            # Additional check: see if we can access basic websocket properties
            if hasattr(self.websocket, 'remote_address'):
                remote_addr = getattr(self.websocket, 'remote_address', None)
                if remote_addr is None:
                    return {
                        'is_healthy': False,
                        'reason': 'WebSocket remote address unavailable'
                    }

            # If we get here, the basic websocket object seems intact
            self.logger.debug("[HEALTH] WebSocket object appears healthy")

        except Exception as e:
            return {
                'is_healthy': False,
                'reason': f'WebSocket state check failed: {e}'
            }

        # Check 4: Are there too many orphaned pending requests?
        pending_count = len(self.pending_requests)
        if pending_count > 5:
            return {
                'is_healthy': False,
                'reason': f'Too many pending requests ({pending_count}), possible deadlock'
            }

        # All checks passed
        return {
            'is_healthy': True,
            'reason': f'Connection healthy - Pending: {pending_count}, WebSocket: ACTIVE'
        }

    def _test_server_ping(self) -> bool:
        """Test server communication during health check"""
        try:
            if not self.websocket or not self.connected:
                return False

            # Send a test ping request during health check
            ping_message = json.dumps({
                'type': 'ping',
                'health_check': True,
                'timestamp': time.time()
            })

            # Send via asyncio from the health check thread
            future = asyncio.run_coroutine_threadsafe(
                self.websocket.send(ping_message),
                self.loop
            )

            # Wait up to 5 seconds for the send operation
            future.result(timeout=5)
            self.logger.debug("[HEALTH] Ping message sent to server successfully")
            return True

        except Exception as e:
            self.logger.debug(f"[HEALTH] Server ping test failed: {e}")
            return False

    def _test_simple_connectivity(self) -> bool:
        """Test if we can send a simple message (non-blocking test)"""
        try:
            if not self.websocket or not self.connected:
                return False

            # Just check if the websocket is ready for sending
            # We won't actually send a ping to avoid complicating the message flow
            proto = self._get_protocol()
            return proto and getattr(proto, "open", False)

        except Exception as e:
            self.logger.debug(f"Simple connectivity test failed: {e}")
            return False

    def _stop_health_check(self):
        """Stop health check timer with enhanced cleanup"""
        if self.health_check_timer:
            try:
                self.health_check_timer.cancel()
                self.logger.debug("[HEALTH] Health check timer stopped")
            except Exception as e:
                self.logger.debug(f"[HEALTH] Timer stop error (usually harmless): {e}")
            finally:
                self.health_check_timer = None

    def _health_check(self):
        """Perform health check and restart if needed"""
        try:
            if not self.connected or not self.is_connection_healthy():
                self._log_message("Health check failed - restarting connection")
                if self.running:
                    # Restart connection
                    asyncio.run_coroutine_threadsafe(self._restart_connection(), self.loop)
        except Exception as e:
            self._log_message(f"Health check error: {e}")
        finally:
            # Schedule next health check
            if self.running:
                self._start_health_check()

    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy"""
        if not self.connected:
            return False

        # Check if websocket is still open
        proto = self._get_protocol()
        if not proto or not getattr(proto, "open", False):
            return False

        # Check heartbeat (if ping was sent more than 2 times of the heartbeat interval)
        if self.last_ping_time > 0 and (time.time() - self.last_ping_time) > self.heartbeat_interval * 2:
            return False

        return True

    async def _restart_connection(self):
        """Restart connection with proper cleanup and timing control"""
        self.logger.info("[RESTART] Connection restart initiated")

        # Stop health check timer to prevent overlapping checks
        self._stop_health_check()

        try:
            # Step 1: Clean up all pending requests
            pending_count = len(self.pending_requests)
            if pending_count > 0:
                self.logger.info(f"[RESTART] Cleaning up {pending_count} pending requests")
                self._cleanup_pending_requests("Connection restarting - clearing pending requests")

            # Step 2: Close current connection
            self.logger.info("[RESTART] Closing current connection")
            await self._close_connection()

            # Step 3: Reset connection state
            self.connected = False
            self.connecting = False
            self._log_connection_state("Connection state reset for restart")

            # Step 4: Wait before reconnecting
            self.logger.info("[RESTART] Waiting 3 seconds before reconnection attempt")
            await asyncio.sleep(3)

            # Step 5: Attempt reconnection
            self.logger.info("[RESTART] Attempting reconnection")
            await self._connect_websocket()

            if self.connected:
                self.logger.info("[RESTART] Connection restart SUCCESS")
            else:
                self.logger.error("[RESTART] Connection restart FAILED")

        except Exception as e:
            self.logger.error(f"[RESTART] Connection restart ERROR: {e}")
            self.connected = False
        finally:
            # Always restart health monitoring after restart attempt
            if self.running:
                self.logger.info("[RESTART] Restarting health monitoring")
                # Wait a bit more before starting health checks to let connection stabilize
                await asyncio.sleep(5)
                self._start_health_check()

    # Send TTS request and return audio data via WebSocket or HTTP
    def send_tts_request(self, text: str, voice: str = "af_heart") -> Optional[bytes]:
        """Send TTS request - simple working version"""
        if not self.connected:
            self._log_message("Not connected - cannot send TTS request")
            return None

        try:
            request = {
                'type': 'tts',
                'text': text,
                'voice': voice
            }

            # Use the simple async pattern that was working
            future = asyncio.run_coroutine_threadsafe(
                self._send_request(request), self.loop
            )
            response = future.result(timeout=60)

            if response and response.get('type') == 'tts_response':
                # Handle HTTP token download (your server uses this method)
                audio_token = response.get('audio_token')
                if audio_token:
                    return self._download_audio_via_http(audio_token)  # Fixed: added underscore
                else:
                    # Fallback to direct base64 audio
                    audio_b64 = response.get('audio')
                    if audio_b64:
                        return base64.b64decode(audio_b64)

            return None
        except Exception as e:
            self._log_message(f"TTS request error: {e}")
            return None

    def send_stt_request(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[Dict[str, str]]:
        """Send STT request - simple working version"""
        if not self.connected:
            self._log_message("Not connected - cannot send STT request")
            return None

        try:
            # Convert numpy array to base64
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio_b64 = base64.b64encode(audio_bytes).decode()

            request = {
                'type': 'stt',
                'audio': audio_b64,
                'sample_rate': sample_rate
            }

            # Use the simple async pattern that was working
            future = asyncio.run_coroutine_threadsafe(
                self._send_request(request), self.loop
            )
            response = future.result(timeout=60)

            if response and response.get('type') == 'stt_response':
                return {
                    'text': response.get('text', ''),
                    'language': response.get('language', 'unknown')
                }

            return None
        except Exception as e:
            self._log_message(f"STT request error: {e}")
            return None


    def _cleanup_pending_requests(self, error_message: str):
        """Clean up pending requests with detailed logging"""
        cleanup_count = 0

        for request_id, future in list(self.pending_requests.items()):
            try:
                if not future.done():
                    future.set_exception(Exception(error_message))
                    cleanup_count += 1
            except Exception as e:
                self.logger.debug(f"Error cleaning up request {request_id}: {e}")

        self.pending_requests.clear()
        self.logger.info(f"🧹 Cleaned up {cleanup_count} pending requests - Reason: {error_message}")

    def _download_audio_via_http(self, audio_token: str) -> Optional[bytes]:
        """Download large audio file via HTTP"""
        try:
            download_url = f"http://{self.host}:{self.http_port}/download_audio/{audio_token}"
            self._log_message(f"Downloading audio via HTTP: {download_url}")

            # Download with timeout and retry logic
            response = requests.get(download_url, timeout=30)

            if response.status_code == 200:
                audio_bytes = response.content
                self._log_message(f"HTTP download successful: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                self._log_message(f"HTTP download failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            self._log_message(f"HTTP download timeout for token: {audio_token}")
            return None
        except requests.exceptions.ConnectionError:
            self._log_message(f"HTTP connection error for token: {audio_token}")
            return None
        except Exception as e:
            self._log_message(f"HTTP download error: {e}")
            return None

    def send_stt_request_from_file(self, file_path: str) -> Optional[Dict[str, str]]:
        """Send STT request from audio file"""
        try:
            audio_data, sample_rate = sf.read(file_path)
            if len(audio_data.shape) > 1:
                audio_data = audio_data[:, 0]
            return self.send_stt_request(audio_data, sample_rate)
        except Exception as e:
            self._log_message(f"STT file request error: {e}")
            return None

    def save_tts_audio(self, audio_bytes: bytes, output_path: str) -> bool:
        """Save TTS audio to file"""
        try:
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            self._log_message(f"Audio saved to: {output_path}")
            return True
        except Exception as e:
            self._log_message(f"Error saving audio: {e}")
            return False

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request and wait for response using queue system"""
        try:
            if not self.websocket:
                raise Exception("WebSocket not connected")

            # Add request ID for response matching
            request_id = str(self.request_id_counter)
            self.request_id_counter += 1
            request['request_id'] = request_id

            # Create response future
            response_future = asyncio.Future()
            self.pending_requests[request_id] = response_future

            await self.websocket.send(json.dumps(request))
            self._log_message(f"Sent {request['type']} request (ID: {request_id})")

            try:
                # Wait for response
                response = await asyncio.wait_for(response_future, timeout=60)
                return response
            finally:
                # Cleanup
                self.pending_requests.pop(request_id, None)

        except asyncio.TimeoutError:
            self._log_message("Request timeout - no response from server")
            return None
        except Exception as e:
            self._log_message(f"Request error: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        """Get detailed client status"""
        return {
            'connected': self.connected,
            'host': self.host,
            'port': self.port,
            'auto_connect_enabled': self.auto_connect_enabled,
            'reconnect_attempts': self.reconnect_attempts,
            'thread_alive': self.thread.is_alive() if self.thread else False,
            'connection_healthy': self.is_connection_healthy()
        }


# Test functions for standalone testing
def test_tts(client, text="Hello, this is a test of the TTS system."):
    """Test TTS functionality"""
    print(f"Testing TTS with text: {text}")
    audio_bytes = client.send_tts_request(text, voice="af_heart")

    if audio_bytes:
        output_file = f"test_tts_{int(time.time())}.wav"
        if client.save_tts_audio(audio_bytes, output_file):
            print(f"TTS test successful! Audio saved to: {output_file}")
            return True
        else:
            print("Failed to save TTS audio")
    else:
        print("TTS test failed")
    return False


def test_stt(client, audio_file_path=None):
    """Test STT functionality"""
    if audio_file_path:
        print(f"Testing STT with file: {audio_file_path}")
        result = client.send_stt_request_from_file(audio_file_path)
    else:
        print("Testing STT with generated audio")
        audio_data = np.zeros(16000, dtype=np.float32)
        result = client.send_stt_request(audio_data)

    if result:
        print(f"STT test successful!")
        print(f"Text: {result['text']}")
        print(f"Language: {result['language']}")
        return True
    else:
        print("STT test failed")
    return False


def main():
    """Main function for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description='WebSocket TTS/STT Client')
    parser.add_argument('--host', default='localhost', help='WebSocket server host')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket server port')
    parser.add_argument('--test-tts', action='store_true', help='Test TTS functionality')
    parser.add_argument('--test-stt', action='store_true', help='Test STT functionality')
    parser.add_argument('--tts-text', default='Hello, this is a test.', help='Text for TTS test')
    parser.add_argument('--stt-file', help='Audio file path for STT test')

    args = parser.parse_args()

    client = WebSocketClient_TTSAndSTT(host=args.host, port=args.port)

    try:
        print(f"Connecting to WebSocket server at {args.host}:{args.port}")
        if not client.start_client():
            print("Failed to connect to server")
            return

        print("Connected successfully!")
        print(f"Status: {client.get_status()}")

        if args.test_tts:
            test_tts(client, args.tts_text)

        if args.test_stt:
            test_stt(client, args.stt_file)

        if not args.test_tts and not args.test_stt:
            print("No tests specified. Use --test-tts or --test-stt")

        time.sleep(2)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Stopping client...")
        client.stop_client()
        print("Client stopped")


if __name__ == "__main__":
    main()