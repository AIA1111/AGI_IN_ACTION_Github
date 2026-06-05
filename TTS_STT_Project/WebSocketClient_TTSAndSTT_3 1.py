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
        # Connection settings
        self.host = host
        self.port = port
        self.websocket_url = f"ws://{host}:{port}"
        self.http_port = 8766  # HTTP server port for large file downloads

        # Connection state
        self.websocket = None
        self.connected = False
        self.connecting = False
        self.should_reconnect = True

        # Threading
        self.loop = None
        self.thread = None
        self.running = False

        # Auto-connect and health monitoring
        self.auto_connect_enabled = False
        self.health_check_timer = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 60  # seconds

        # Heartbeat
        self.last_ping_time = 0
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None

        # Config file
        self.config_file = "websocket_config.json"

        # Response handling for concurrent requests
        self.pending_requests = {}
        self.request_id_counter = 0

        # Callbacks for GUI updates
        self.status_callback = None
        self.log_callback = None

        # Logging
        self.logger = self._setup_logger()

        # Load config and auto-connect if enabled
        self.load_config()
        if self.auto_connect_enabled:
            self.start_client()

    def _get_protocol(self):
        """Unwrap protocol from ClientConnection if needed"""
        if self.websocket is None:
            return None
        # Some versions of websockets return ClientConnection with .protocol
        return getattr(self.websocket, "protocol", self.websocket)

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for WebSocket client"""
        logger = logging.getLogger(f"WSClient_{self.port}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

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

    def load_config(self):
        """Load WebSocket configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.host = config.get('host', self.host)
                    self.port = config.get('port', self.port)
                    self.auto_connect_enabled = config.get('auto_connect_enabled', False)
                    self.websocket_url = f"ws://{self.host}:{self.port}"
                    self._log_message(
                        f"Config loaded: {self.host}:{self.port}, Auto-connect: {self.auto_connect_enabled}")
        except Exception as e:
            self._log_message(f"Config load error: {e}")

    def save_config(self, host: str = None, port: int = None, auto_connect: bool = None):
        """Save WebSocket configuration to file"""
        try:
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

            self._log_message(f"Config saved: {self.host}:{self.port}, Auto-connect: {self.auto_connect_enabled}")
            return True
        except Exception as e:
            self._log_message(f"Config save error: {e}")
            return False

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
        """Establish WebSocket connection"""
        if self.connecting:
            return

        self.connecting = True
        try:
            self._log_message(f"Connecting to {self.websocket_url}")
            self._update_status("Connecting...", 'orange')

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

            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except Exception as e:
            self.connected = False
            self.connecting = False
            self._update_status("Connection Failed", 'red')
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

    def _start_health_check(self):
        """Start periodic health check"""
        self._stop_health_check()  # Ensure no duplicate timers
        self.health_check_timer = threading.Timer(600, self._health_check)  # 10 minutes interval check the health...I tested it is working, but always restarting the connection
        self.health_check_timer.daemon = True
        self.health_check_timer.start()

    def _stop_health_check(self):
        """Stop health check timer"""
        if self.health_check_timer:
            self.health_check_timer.cancel()
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
        """Restart WebSocket connection"""
        try:
            await self._close_connection()
            self.connected = False
            await asyncio.sleep(1)
            await self._connect_websocket()
        except Exception as e:
            self._log_message(f"Restart connection error: {e}")

    # Send TTS request and return audio data via WebSocket or HTTP
    def send_tts_request(self, text: str, voice: str = "af_heart") -> Optional[bytes]:
        """Send TTS request and return audio data via WebSocket or HTTP"""
        if not self.connected:
            self._log_message("Not connected - cannot send TTS request")
            return None

        try:
            request = {
                'type': 'tts',
                'text': text,
                'voice': voice
            }

            # Use asyncio to send request
            future = asyncio.run_coroutine_threadsafe(
                self._send_request(request), self.loop
            )
            response = future.result(timeout=60)

            if response and response.get('type') == 'tts_response':
                audio_size = response.get('audio_size', 0)
                audio_token = response.get('audio_token')

                self._log_message(f"TTS response: HTTP delivery, size: {audio_size} bytes")

                if audio_token:
                    return self._download_audio_via_http(audio_token)
                else:
                    self._log_message("No audio token received in TTS response")

            return None
        except Exception as e:
            self._log_message(f"TTS request error: {e}")
            return None

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

    def send_stt_request(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[Dict[str, str]]:
        """Send STT request with audio data"""
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

            # Use asyncio to send request
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