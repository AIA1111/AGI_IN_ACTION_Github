import asyncio
import websockets
import json
import base64
import logging
import threading
import time
import io
import numpy as np
import soundfile as sf
from typing import Optional, Dict, Any


class WebSocketClient_TTSAndSTT:
    """WebSocket client for TTS and STT services"""

    def __init__(self, host="localhost", port=8765, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.websocket = None
        self.connected = False
        self.loop = None
        self.thread = None

        # Setup logging
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_client(self):
        """Start the WebSocket client in a separate thread"""
        if self.thread and self.thread.is_alive():
            self.logger.warning("Client already running")
            return True

        try:
            self.thread = threading.Thread(target=self._run_client, daemon=True)
            self.thread.start()

            # Wait for connection with timeout
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < 10:
                time.sleep(0.1)

            return self.connected
        except Exception as e:
            self.logger.error(f"Failed to start client: {e}")
            return False

    def _run_client(self):
        """Run the asyncio event loop in the thread"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._connect())
        except Exception as e:
            self.logger.error(f"Client thread error: {e}")

    async def _connect(self):
        """Connect to WebSocket server"""
        try:
            uri = f"ws://{self.host}:{self.port}"
            self.logger.info(f"Connecting to {uri}")

            self.websocket = await websockets.connect(uri)
            self.connected = True
            self.logger.info("Connected to WebSocket server")

            # Keep connection alive
            await self.websocket.wait_closed()
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.connected = False

    def stop_client(self):
        """Stop the WebSocket client"""
        try:
            if self.websocket:
                if self.loop and not self.loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
                    future.result(timeout=5)

            self.connected = False
            self.logger.info("Client stopped")
        except Exception as e:
            self.logger.error(f"Error stopping client: {e}")

    def send_tts_request(self, text: str, voice: str = "af_heart") -> Optional[bytes]:
        """
        Send TTS request and return audio bytes

        Args:
            text: Text to convert to speech
            voice: Voice to use for generation

        Returns:
            Audio bytes (WAV format) or None if failed
        """
        if not self.connected:
            self.logger.error("Not connected to server")
            return None

        try:
            request = {
                "type": "tts",
                "text": text,
                "voice": voice
            }

            future = asyncio.run_coroutine_threadsafe(
                self._send_request(request), self.loop
            )
            response = future.result(timeout=self.timeout)

            if response and response.get('type') == 'tts_response':
                audio_b64 = response.get('audio')
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    self.logger.info(f"TTS response received: {len(audio_bytes)} bytes")
                    return audio_bytes
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                self.logger.error(f"TTS request failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"TTS request error: {e}")

        return None

    def send_stt_request(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[Dict[str, str]]:
        """
        Send STT request and return transcription

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio

        Returns:
            Dictionary with 'text' and 'language' or None if failed
        """
        if not self.connected:
            self.logger.error("Not connected to server")
            return None

        try:
            # Convert audio to bytes
            buffer = io.BytesIO()
            sf.write(buffer, audio_data, sample_rate, format='WAV')
            audio_bytes = buffer.getvalue()
            audio_b64 = base64.b64encode(audio_bytes).decode()

            request = {
                "type": "stt",
                "audio": audio_b64
            }

            future = asyncio.run_coroutine_threadsafe(
                self._send_request(request), self.loop
            )
            response = future.result(timeout=self.timeout)

            if response and response.get('type') == 'stt_response':
                result = {
                    'text': response.get('text', ''),
                    'language': response.get('language', 'unknown')
                }
                self.logger.info(f"STT response: {result['text'][:50]}...")
                return result
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                self.logger.error(f"STT request failed: {error_msg}")

        except Exception as e:
            self.logger.error(f"STT request error: {e}")

        return None

    def send_stt_request_from_file(self, audio_file_path: str) -> Optional[Dict[str, str]]:
        """
        Send STT request from audio file

        Args:
            audio_file_path: Path to audio file

        Returns:
            Dictionary with 'text' and 'language' or None if failed
        """
        try:
            audio_data, sample_rate = sf.read(audio_file_path)
            return self.send_stt_request(audio_data, sample_rate)
        except Exception as e:
            self.logger.error(f"Error reading audio file: {e}")
            return None

    def save_tts_audio(self, audio_bytes: bytes, output_path: str) -> bool:
        """
        Save TTS audio bytes to file

        Args:
            audio_bytes: Audio data as bytes
            output_path: Path to save the audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            self.logger.info(f"Audio saved to: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving audio: {e}")
            return False

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request and wait for response"""
        try:
            if not self.websocket:
                raise Exception("WebSocket not connected")

            # Send request
            await self.websocket.send(json.dumps(request))
            self.logger.info(f"Sent {request['type']} request")

            # Wait for response with longer timeout
            response_str = await asyncio.wait_for(self.websocket.recv(), timeout=60)
            response = json.loads(response_str)
            self.logger.info(f"Received response: {response.get('type', 'unknown')}")

            return response
        except asyncio.TimeoutError:
            self.logger.error("Request timeout - no response from server")
            return None
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected

    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            'connected': self.connected,
            'host': self.host,
            'port': self.port,
            'thread_alive': self.thread.is_alive() if self.thread else False
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
        # Generate test audio (silence for demo)
        print("Testing STT with generated audio")
        audio_data = np.zeros(16000, dtype=np.float32)  # 1 second of silence
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

    # Create client
    client = WebSocketClient_TTSAndSTT(host=args.host, port=args.port)

    try:
        # Start client
        print(f"Connecting to WebSocket server at {args.host}:{args.port}")
        if not client.start_client():
            print("Failed to connect to server")
            return

        print("Connected successfully!")
        print(f"Status: {client.get_status()}")

        # Run tests
        if args.test_tts:
            test_tts(client, args.tts_text)

        if args.test_stt:
            test_stt(client, args.stt_file)

        if not args.test_tts and not args.test_stt:
            print("No tests specified. Use --test-tts or --test-stt")

        # Keep alive for a moment
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