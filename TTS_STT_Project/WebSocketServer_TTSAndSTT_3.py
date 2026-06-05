####Insert your PySimpleGUI distribution key at the top
PySimpleGUI_License = """elyIJgMoaqWzNll5bHnuNAlhVaHhlKwCZhSlIj6KI6kpRep6cU3SRPyNafW3JZ1PdsGclzv8bAiLIBsZI7kVxEp5Y42cVRuQc822VnJARuCeIO6RMaTUcWzKNbzlIdz8NojQchxsNoSdwtivTJGQlljeZvWq56z0ZhUGRalYceGsx8vYerWN1hlQbZn2RxWkZMXNJZzOa1WH9BuVIFjLoGipNuSi4XwpIgimwkirTYmaFitOZaUcZ4pdc8n1N602Iljyoai5ScmVFnntYWWZ50uZYeXWROosIXikwrirTEmOFBtHZNUNxHhlch3uQRi5O8iXJ9C8Z2WHhLlScjmdEei1LRCkJ8DYbm2R1mwfYpWq5g5iIXjuoNiIS4mFFdnDYDW65zukYSXxR5oZIEEOJqlEavGZVeyxYiS8IHs8I0kwN71qcY3lRPvIbPWIVByOSKUnQGiQOpihIhy8M6DIUK1bM8i3ImsYITkvRHhPdnG8VoJfc63LNu1KZVWsQ3iTOgiGIJybM1D7Iy1bLeTdAux4LgTREe5pIwipwoiXRiG6FM0QZWUoVg4EcNGHlFyGZUXMMLi0OniBIZyqMIDVIs1jLdTBAu1uLeTVEo0lIFiFwXiVRuW61EhXaLWBxFB7Z1GYRly0ZFXFNkzvI6jqoqiHaFmTFon7YMWT5buOYsXNRiozYlmZVgo2Z0X3J5hYMZzFMOzeMQ09BfnvbxWNFtpxbuCR52jZbv2X05ikL1CzJkJWUwEFF9kxZyHWJ4lTc03CMbiXOkicID0PNxSo4C5yMHCn4gymMMj7ITuAMhT0Q83WIQnX0d=J517c7d5fae65077acdc2471d2e926436011f50cc3bff5e606996187bbc87cb0a4796f69a65646f4f2401c26398c4df3c2e20ac1bdeb726222b3535af30177dbcda327d862b8ef3d121801906e44ce44ce74e02331e3f88e13586c3337e7d4b113f826187ea2a355b3075917c78aa05926b289cf8738a54267aa4915a7f14840a36d4d4abc646871adbb8d9bf078f67f1e8461fde9cf36a2a5def3e81ce135a48eeb90c5d39a04e85af461d99f296a8677f30403585d5bb3eb9bec197839c48f1e4365fa61bd8b798a73e11b4c5de4285f3bfcb92434865cc97c01064fa2da9241ae20be5d353e47db24a67d0458bf8b95b51226ad2e3cefacb628e38d343183a672022e4bec60007d2004e040f64d7f5dc4cfdc95e1676717fb7ac0cfdff6f5ce5426003db19b59a1407e89b7d3aff88592a0d6d26b7dc3c2dc5903fa3bf2ffa6a3ffb6991ae1a89e4a24e215401673b9fad941e4b142a751654c7028d616835a554764579e316a98f22eabad4f98395c807633d28f9372488dcc39702c95545a413b990146c6d9b9030e18709d2c10fbe7d8510a81e9088349ea5a870a51e5d3cda58754b22e686394e3ecc5a43e47a6d4e374fc1972f7e95be48c7863a51de076112dd2415591c2c2851ddbf12c91de33d4e2aa28c8418c59c70a5dcd523cbc7df76ca12fd4e50be0cde747ebe6b43f21821190ed58faf2a6e416850145b10"""

import PySimpleGUI as sg
import sys
import torch
import os
import threading
import pygame
import shutil
import torchaudio
import time
import json
import logging
import tempfile
import multiprocessing
import whisper
import wave
import numpy as np
import asyncio
import websockets
import base64
import io
import soundfile as sf
from kokoro import KPipeline
import sounddevice as sd
import atexit
import signal
###HTTP server imports
from flask import Flask, send_file, request, jsonify
import uuid
import random
import re
from threading import Thread


# Executable environment protection
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Windows-compatible logging setup
def setup_logging():
    """Configure logging with Windows-compatible encoding"""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    os.makedirs('./logs', exist_ok=True)

    file_handler = logging.FileHandler('./logs/websocket_tts_stt.log', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()
sg.theme('DarkBlue3')

# Global variables
pipeline = None
whisper_model = None
is_generating = False
is_recording = False
websocket_server = None
server_running = False
conversation_history = []
available_voices = ['af_heart', 'af_bella', 'af_sarah', 'af_sky', 'af_nicole',
                    'am_adam', 'am_michael', 'bf_emma', 'bf_isabella', 'bm_george']
# HTTP Server globals for large file transfer
http_app = Flask(__name__)
http_server = None
HTTP_PORT = 8766  # Different port from WebSocket
TEMP_AUDIO_DIR = "./temp_audio"

# Create temp directory for audio files
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


def cleanup_old_temp_files(max_age_minutes=30):
    """Clean up temporary files older than specified age"""
    try:
        current_time = time.time()
        cleanup_count = 0

        for filename in os.listdir(TEMP_AUDIO_DIR):
            if filename.startswith('audio_') and filename.endswith('.flac'):
                file_path = os.path.join(TEMP_AUDIO_DIR, filename)
                file_age_seconds = current_time - os.path.getmtime(file_path)

                # If file is older than max_age_minutes, delete it
                if file_age_seconds > (max_age_minutes * 60):
                    try:
                        os.remove(file_path)
                        cleanup_count += 1
                        logger.info(f"Cleaned up old temp file: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up {filename}: {e}")

        if cleanup_count > 0:
            logger.info(f"Cleanup completed: removed {cleanup_count} old files")

    except Exception as e:
        logger.error(f"Cleanup process error: {e}")


def start_cleanup_scheduler():
    """Start background thread for periodic cleanup"""

    def cleanup_loop():
        while True:
            time.sleep(300)  # Run cleanup every 5 minutes
            cleanup_old_temp_files(max_age_minutes=30)  # Clean files older than 30 minutes

    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("Cleanup scheduler started (runs every 5 minutes)")


# ONLY ADDITION: Connection management variables
active_connections = set()
MAX_CONNECTIONS = 10

# Paths
DEFAULT_SAVE_PATH = "./generated_audio/"
WHISPER_MODEL_PATH = "./models/whisper-large-v3/large-v3.pt"
KOKORO_MODEL_PATH = "./models/kokoro-82m"

# Audio settings for Whisper
CHANNELS = 1
RATE = 16000

# WebSocket settings
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765

# ONLY ADDITION: Cleanup function
def cleanup_on_exit():
    """Clean up resources on exit"""
    global websocket_server, server_running
    try:
        if websocket_server and server_running:
            websocket_server.close()
            server_running = False
        # Close all active connections
        for conn in list(active_connections):
            try:
                asyncio.create_task(conn.close())
            except:
                pass
        active_connections.clear()
        logger.info("Cleanup completed")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# ONLY ADDITION: Register cleanup
atexit.register(cleanup_on_exit)

def get_kokoro_model_path(custom_path=None):
    """Get Kokoro model path"""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    mac_path = "./models/kokoro-82m"
    if os.path.exists(mac_path):
        return mac_path
    return None

def load_whisper_model():
    """Load Whisper model"""
    global whisper_model
    try:
        if os.path.exists(WHISPER_MODEL_PATH):
            whisper_model = whisper.load_model(WHISPER_MODEL_PATH)
            logger.info(f"Whisper loaded from: {WHISPER_MODEL_PATH}")
        else:
            whisper_model = whisper.load_model("large-v3")
            logger.info("Whisper loaded from cache")
        return True
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        return False

def load_kokoro_model():
    """Load Kokoro model"""
    global pipeline
    try:
        model_path = get_kokoro_model_path()
        if not model_path:
            raise Exception("Kokoro model path not found")

        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_DATASETS_OFFLINE'] = '1'

        pipeline = KPipeline(lang_code='a')
        logger.info("Kokoro loaded successfully")

        pygame.mixer.pre_init(frequency=24000, size=-16, channels=1, buffer=1024)
        pygame.mixer.init()
        return True
    except Exception as e:
        logger.error(f"Failed to load Kokoro model: {e}")
        return False

def record_audio_stt(duration, window):
    """Record audio with sounddevice"""
    global is_recording
    is_recording = True

    try:
        window['stt_status'].update(f"🎤 Recording for {duration} seconds...")
        window['stt_record5'].update(disabled=True)
        window['stt_record10'].update(disabled=True)
        window['stt_progress'].update_bar(0, duration)

        audio_data = sd.rec(int(duration * RATE), samplerate=RATE, channels=1, dtype='float32')

        for i in range(duration * 10):
            if not is_recording:
                break
            time.sleep(0.1)
            window['stt_progress'].update_bar(i / 10, duration)

        sd.wait()

        if is_recording and whisper_model:
            window['stt_status'].update("🔄 Transcribing...")
            result = whisper_model.transcribe(audio_data.flatten())

            window['stt_output'].update(result['text'])
            window['stt_language'].update(f"Language: {result['language']}")
            window['stt_status'].update("✅ Transcription complete!")

    except Exception as e:
        window['stt_status'].update(f"❌ Error: {e}")
        logger.error(f"Recording error: {e}")
    finally:
        is_recording = False
        window['stt_record5'].update(disabled=False)
        window['stt_record10'].update(disabled=False)

def test_microphone():
    """Test microphone with sounddevice"""
    try:
        devices = sd.query_devices()
        input_devices = [f"Device {i}: {dev['name']}" for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]

        if input_devices:
            sg.popup_scrolled('\n'.join(input_devices), title="Available Input Devices", size=(60, 15))
        else:
            sg.popup_error("No input devices found!")

    except Exception as e:
        sg.popup_error(f"Microphone test failed: {e}")

def update_tts_log(window, message):
    """Update TTS log display"""
    try:
        clean_message = message.replace('✅', '[SUCCESS]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]').replace(
            '🔄', '[LOADING]')
        current_log = window['tts_log'].get()
        timestamp = time.strftime("%H:%M:%S")
        new_log = f"{current_log}[{timestamp}] {clean_message}\n"
        window['tts_log'].update(new_log)
        logger.info(clean_message)
    except Exception as e:
        logger.error(f"Failed to update TTS log: {e}")

def generate_speech_kokoro(text, voice, save_path, filename_prefix, add_timestamp, window):
    """Generate speech using Kokoro"""
    global is_generating, conversation_history, pipeline

    if is_generating:
        update_tts_log(window, "[WARNING] Generation already in progress")
        return None

    is_generating = True
    start_time = time.time()

    try:
        if not pipeline:
            raise Exception("Kokoro pipeline not initialized")

        update_tts_log(window, f"Starting generation with voice: {voice}")
        window['tts_status'].update("Generating speech...")
        window['tts_generate'].update(disabled=True)
        window['tts_generate_long'].update(disabled=True)

        os.makedirs(save_path, exist_ok=True)

        timestamp = int(time.time()) if add_timestamp else ""
        filename = f"{filename_prefix}_{timestamp}.wav" if timestamp else f"{filename_prefix}.wav"
        output_file = os.path.join(save_path, filename)

        update_tts_log(window, f"Generating audio for {len(text)} characters")

        audio_data = []
        generator = pipeline(text, voice=voice)

        for i, (graphemes, phonemes, audio) in enumerate(generator):
            if hasattr(audio, 'numpy'):
                audio = audio.numpy()
            elif torch.is_tensor(audio):
                audio = audio.detach().cpu().numpy()

            audio_data.append(audio)
            update_tts_log(window, f"Generated segment {i + 1}: {len(graphemes)} chars")

        if audio_data:
            full_audio = np.concatenate(audio_data)
            sf.write(output_file, full_audio, 24000)

            generation_time = time.time() - start_time
            audio_duration = len(full_audio) / 24000

            conversation_entry = f"[{voice}] {text[:40]}{'...' if len(text) > 40 else ''}"
            conversation_history.append(conversation_entry)

            window['tts_audio_file'].update(output_file)
            window['tts_gen_time'].update(f"{generation_time:.1f}s")
            window['tts_audio_duration'].update(f"{audio_duration:.1f}s")
            window['tts_history'].update(conversation_history[-10:])
            window['tts_status'].update("✅ Generation complete!")

            update_tts_log(window, f"[SUCCESS] Audio saved: {filename}")
            update_tts_log(window, f"Generation time: {generation_time:.1f}s, Duration: {audio_duration:.1f}s")

        else:
            raise Exception("No audio data generated")

    except Exception as e:
        update_tts_log(window, f"[ERROR] Generation failed: {e}")
        window['tts_status'].update(f"❌ Error: {e}")

    finally:
        is_generating = False
        window['tts_generate'].update(disabled=False)
        window['tts_generate_long'].update(disabled=False)

def play_audio(file_path, window):
    """Play audio file using pygame"""
    try:
        if not os.path.exists(file_path):
            raise Exception("Audio file not found")

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        update_tts_log(window, f"Playing: {os.path.basename(file_path)}")

    except Exception as e:
        update_tts_log(window, f"[ERROR] Playback failed: {e}")

def stop_audio(window):
    """Stop audio playback"""
    try:
        pygame.mixer.music.stop()
        update_tts_log(window, "Audio stopped")
    except Exception as e:
        update_tts_log(window, f"[ERROR] Stop error: {e}")

# ONLY MODIFICATION: Enhanced WebSocket handler with connection management
async def handle_websocket_connection(websocket, path, window):
    """Handle WebSocket connections"""
    try:
        # ONLY ADDITION: Connection limit check
        if len(active_connections) >= MAX_CONNECTIONS:
            await websocket.close(code=1013, reason="Server full")
            return

        # ONLY ADDITION: Add to active connections
        active_connections.add(websocket)

        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        def update_gui_log(message):
            try:
                window['ws_log'].print(f"[{time.strftime('%H:%M:%S')}] {message}")
            except:
                pass

        update_gui_log(f"Client connected: {client_info}")

        async for message in websocket:
            try:
                data = json.loads(message)
                request_type = data.get('type')

                if request_type == 'tts':
                    text = data.get('text', '')
                    voice = data.get('voice', 'af_heart')

                    window['tts_text'].update(text)
                    window['tts_voice'].update(voice)
                    window['tts_status'].update("🌐 Processing WebSocket TTS request...")

                    update_gui_log(f"TTS request: {text[:50]}...")

                    if pipeline:
                        audio_data = []
                        generator = pipeline(text, voice=voice)

                        for graphemes, phonemes, audio in generator:
                            if hasattr(audio, 'numpy'):
                                audio = audio.numpy()
                            elif torch.is_tensor(audio):
                                audio = audio.detach().cpu().numpy()
                            audio_data.append(audio)

                        if audio_data:
                            full_audio = np.concatenate(audio_data)

                            buffer = io.BytesIO()
                            sf.write(buffer, full_audio, 24000, format='FLAC')
                            audio_bytes = buffer.getvalue()
                            audio_size = len(audio_bytes)

                            # PURE HTTP DELIVERY: All audio files delivered via HTTP regardless of size
                            audio_token = f"audio_{int(time.time())}_{random.randint(1000, 9999)}"
                            temp_audio_path = os.path.join(TEMP_AUDIO_DIR, f"{audio_token}.flac")

                            # Save audio file for HTTP download
                            with open(temp_audio_path, 'wb') as f:
                                f.write(audio_bytes)

                            response = {
                                'type': 'tts_response',
                                'audio_token': audio_token,
                                'voice': voice,
                                'encoding': 'flac',
                                'delivery_method': 'http',
                                'audio_size': audio_size,
                                'request_id': data.get('request_id')
                            }
                            await websocket.send(json.dumps(response))
                            update_gui_log(f"Audio saved for HTTP download: {audio_size} bytes, token: {audio_token}")
                            window['tts_status'].update("✅ HTTP TTS token sent")
                        else:
                            await websocket.send(json.dumps({'type': 'error', 'message': 'Audio generation failed',
                                                             'request_id': data.get('request_id')}))
                    else:
                        await websocket.send(json.dumps({'type': 'error', 'message': 'Kokoro model not loaded',
                                                         'request_id': data.get('request_id')}))

                elif request_type == 'stt':
                    audio_b64 = data.get('audio')
                    window['stt_status'].update("🌐 Processing WebSocket STT request...")
                    update_gui_log("STT request received")
                    if audio_b64 and whisper_model:
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            # Right after audio_bytes = base64.b64decode(audio_b64) add this for debug
                            debug_file = f"debug_audio_{int(time.time())}.raw"
                            with open(debug_file, "wb") as f:
                                f.write(audio_bytes)
                            print(f"Saved {len(audio_bytes)} bytes to {debug_file}")

                            # Proper PCM to float conversion for Whisper - this ensures accurate transcription
                            try:
                                # Android sends 16-bit PCM, convert to float32 in range [-1, 1]
                                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                                audio_data = audio_int16.astype(np.float32) / 32768.0

                                # Ensure the audio length is reasonable (at least 0.5 seconds of audio)
                                min_samples = 8000  # 0.5 seconds at 16kHz
                                if len(audio_data) < min_samples:
                                    raise Exception(
                                        f"Audio too short: {len(audio_data)} samples, need at least {min_samples}")

                                # Normalize audio to prevent clipping - this helps Whisper accuracy
                                max_val = np.max(np.abs(audio_data))
                                if max_val > 0:
                                    audio_data = audio_data / max_val * 0.9

                                print(f"Audio stats: length={len(audio_data)}, max={max_val:.3f}, sample_rate=16000")

                            except Exception as audio_error:
                                raise Exception(f"Audio format error: {audio_error}")

                            result = whisper_model.transcribe(audio_data, language='en')
                            text = result['text']
                            language = result.get('language', 'unknown')
                            response = {
                                'type': 'stt_response',
                                'text': text,
                                'language': language,
                                'request_id': data.get('request_id')  # ADDED
                            }
                            await websocket.send(json.dumps(response))
                            window['stt_output'].update(text)
                            window['stt_language'].update(f"Language: {language}")
                            window['stt_status'].update("✅ WebSocket STT completed")
                            update_gui_log(f"STT response: {text[:50]}...")
                        except Exception as e:
                            await websocket.send(
                                json.dumps({'type': 'error', 'message': f'STT processing failed: {str(e)}',
                                            'request_id': data.get('request_id')}))
                            update_gui_log(f"STT error: {e}")
                    else:
                        await websocket.send(json.dumps({'type': 'error', 'message': 'STT processing failed',
                                                         'request_id': data.get('request_id')}))

                # Handle heartbeat ping
                elif request_type == 'ping':  # CHANGED from 'if' to 'elif'
                    pong_response = {
                        'type': 'pong',
                        'timestamp': time.time(),
                        'server_time': time.strftime('%H:%M:%S'),
                        'request_id': data.get('request_id')  # ADDED
                    }
                    await websocket.send(json.dumps(pong_response))
                    continue

            except json.JSONDecodeError:
                await websocket.send(json.dumps({'type': 'error', 'message': 'Invalid JSON'}))
                # Continue processing, don't break
            except Exception as e:
                try:
                    await websocket.send(json.dumps({'type': 'error', 'message': str(e)}))
                except:
                    pass  # If can't send error, continue anyway
                logger.error(f"Request error: {e}")
                # Continue processing, don't break

    except websockets.exceptions.ConnectionClosed:
        update_gui_log(f"Client disconnected: {client_info}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # ONLY ADDITION: Remove from active connections
        active_connections.discard(websocket)

async def start_websocket_server(window):
    """Start WebSocket server"""
    global websocket_server, server_running

    try:
        async def handler(websocket):
            await handle_websocket_connection(websocket, None, window)

        websocket_server = await websockets.serve(
            handler,
            WEBSOCKET_HOST,
            WEBSOCKET_PORT,
            max_size=20 * 1024 * 1024  ###--Now, it can handle a 20 MB of Audio files
        )
        server_running = True
        window['ws_status'].update("🟢 Running", text_color='green')
        window['ws_log'].print(
            f"[{time.strftime('%H:%M:%S')}] WebSocket server started on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
        logger.info(f"WebSocket server started on {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")

        await websocket_server.wait_closed()
    except Exception as e:
        server_running = False
        window['ws_status'].update("🔴 Error", text_color='red')
        window['ws_log'].print(f"[{time.strftime('%H:%M:%S')}] Server error: {e}")
        logger.error(f"WebSocket server error: {e}")

def stop_websocket_server(window):
    """Stop WebSocket server"""
    global websocket_server, server_running

    if websocket_server:
        websocket_server.close()
        server_running = False
        window['ws_status'].update("🔴 Stopped", text_color='red')
        window['ws_log'].print(f"[{time.strftime('%H:%M:%S')}] WebSocket server stopped")

def create_layout():
    """Create tabbed GUI layout"""

    # STT Tab
    stt_tab = [
        [sg.Text('🎙️ Whisper STT Tester', font=('Arial', 16, 'bold'), justification='center')],
        [sg.HSeparator()],

        [sg.Text('Model Status:', font=('Arial', 10, 'bold')),
         sg.Text('Loading...', key='stt_model_status', text_color='yellow')],

        [sg.HSeparator()],

        [sg.Text('Recording Controls:', font=('Arial', 12, 'bold'))],
        [sg.Button('Record 5 Seconds', key='stt_record5', size=(15, 2), disabled=True),
         sg.Button('Record 10 Seconds', key='stt_record10', size=(15, 2), disabled=True),
         sg.Button('Stop Recording', key='stt_stop', size=(15, 2))],

        [sg.Text('Progress:'), sg.ProgressBar(10, orientation='h', size=(40, 20), key='stt_progress')],
        [sg.Text('Status:'), sg.Text('Ready', key='stt_status', size=(50, 1))],

        [sg.HSeparator()],

        [sg.Text('Transcription Results:', font=('Arial', 12, 'bold'))],
        [sg.Text('Language:'), sg.Text('Unknown', key='stt_language', text_color='cyan')],
        [sg.Text('Transcribed Text:')],
        [sg.Multiline('', key='stt_output', size=(70, 8), disabled=True, background_color='black', text_color='white')],

        [sg.HSeparator()],
        [sg.Button('Clear STT Results', key='stt_clear'), sg.Button('Test Microphone', key='stt_test_mic')]
    ]

    # TTS Tab
    tts_left_column = [
        [sg.Text('🎵 Kokoro-82M TTS', font=('Arial', 14, 'bold'))],
        [sg.HSeparator()],

        [sg.Text('Model Status:', font=('Arial', 10, 'bold'))],
        [sg.Text('Loading...', key='tts_model_status', text_color='yellow')],
        [sg.HSeparator()],

        [sg.Text('Text to Speak:', font=('Arial', 10, 'bold'))],
        [sg.Multiline('Hello! I am excited to talk to you.', key='tts_text', size=(50, 8))],

        [sg.Text('Voice:', font=('Arial', 10, 'bold'))],
        [sg.Combo(available_voices, default_value='af_heart', key='tts_voice', size=(15, 1))],

        [sg.HSeparator()],
        [sg.Button('Generate Speech', key='tts_generate', size=(15, 2), disabled=True),
         sg.Button('Generate Long Text', key='tts_generate_long', size=(15, 2), disabled=True)],
        [sg.Button('Play Audio', key='tts_play', size=(12, 1)),
         sg.Button('Stop Audio', key='tts_stop_audio', size=(12, 1)),
         sg.Button('Save Audio', key='tts_save', size=(12, 1))],

        [sg.HSeparator()],
        [sg.Text('Status:'), sg.Text('Ready', key='tts_status')],
        [sg.Text('Generated:'), sg.Text('None', key='tts_audio_file', size=(40, 1))],
        [sg.Text('Gen Time:'), sg.Text('0.0s', key='tts_gen_time'),
         sg.Text('Duration:'), sg.Text('0.0s', key='tts_audio_duration')]
    ]

    tts_right_column = [
        [sg.Text('Audio Settings', font=('Arial', 12, 'bold'))],
        [sg.HSeparator()],

        [sg.Frame('Output Settings', [
            [sg.Text('Save Path:')],
            [sg.Input(DEFAULT_SAVE_PATH, key='tts_save_path', size=(25, 1)), sg.FolderBrowse()],
            [sg.Text('Filename:'), sg.Input('kokoro_audio', key='tts_filename_prefix', size=(15, 1))],
            [sg.Checkbox('Add timestamp', key='tts_add_timestamp', default=True)]
        ])],

        [sg.Text('Generation Log:', font=('Arial', 10, 'bold'))],
        [sg.Multiline('', key='tts_log', size=(35, 8), disabled=True, autoscroll=True)],

        [sg.Text('Recent Generations:', font=('Arial', 10, 'bold'))],
        [sg.Listbox([], key='tts_history', size=(35, 4))],
        [sg.Button('Clear TTS History', key='tts_clear_history')]
    ]

    tts_tab = [
        [sg.Column(tts_left_column, vertical_alignment='top'),
         sg.VSeparator(),
         sg.Column(tts_right_column, vertical_alignment='top')]
    ]

    # WebSocket Server Tab
    ws_tab = [
        [sg.Text('🌐 WebSocket Server', font=('Arial', 16, 'bold'), justification='center')],
        [sg.HSeparator()],

        [sg.Text('Server Configuration:', font=('Arial', 12, 'bold'))],
        [sg.Text('Host:'), sg.Input(WEBSOCKET_HOST, key='ws_host', size=(15, 1)),
         sg.Text('Port:'), sg.Input(str(WEBSOCKET_PORT), key='ws_port', size=(8, 1))],

        [sg.Text('Status:'), sg.Text('🔴 Stopped', key='ws_status', text_color='red')],

        [sg.HSeparator()],

        [sg.Button('Start Server', key='ws_start', size=(12, 2)),
         sg.Button('Stop Server', key='ws_stop', size=(12, 2), disabled=True),
         sg.Button('Clear Log', key='ws_clear_log', size=(12, 2))],

        [sg.HSeparator()],

        [sg.Text('Server Information:', font=('Arial', 12, 'bold'))],
        [sg.Text('• POST /tts - Text to Speech', font=('Arial', 9))],
        [sg.Text('• POST /stt - Speech to Text', font=('Arial', 9))],
        [sg.Text('• JSON format: {"type": "tts/stt", "text/audio": "..."}', font=('Arial', 9))],

        [sg.HSeparator()],

        [sg.Text('Server Log:', font=('Arial', 12, 'bold'))],
        [sg.Multiline('', key='ws_log', size=(80, 15), disabled=True, autoscroll=True, background_color='black',
                      text_color='white')]
    ]

    # Main layout with tabs
    layout = [
        [sg.TabGroup([
            [sg.Tab('Whisper STT', stt_tab, key='tab_stt')],
            [sg.Tab('Kokoro TTS', tts_tab, key='tab_tts')],
            [sg.Tab('WebSocket Server', ws_tab, key='tab_ws')]
        ], key='tab_group')],
        [sg.HSeparator()],
        [sg.Button('Exit', key='exit', button_color=('white', 'red'))]
    ]

    return layout

###---HTTP server code START---####
# HTTP Server for large audio file downloads
@http_app.route('/download_audio/<audio_token>')
def download_audio(audio_token):
    """Serve audio files via HTTP download"""
    try:
        # Security: Validate token format to prevent directory traversal
        if not re.match(r'^audio_[0-9]+_[0-9]+$', audio_token):
            logger.warning(f"Invalid audio token format: {audio_token}")
            return jsonify({"error": "Invalid token format"}), 400

        audio_file = os.path.join(TEMP_AUDIO_DIR, f"{audio_token}.flac")

        if os.path.exists(audio_file):
            logger.info(f"Serving audio file: {audio_token}.flac ({os.path.getsize(audio_file)} bytes)")

            def remove_file_after_send(response):
                """Clean up temporary file after successful download"""
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                        logger.info(f"Cleaned up temporary file: {audio_token}.flac")
                except Exception as e:
                    logger.warning(f"Failed to clean up {audio_token}.flac: {e}")
                return response

            # Send file with cleanup callback
            response = send_file(
                audio_file,
                as_attachment=True,
                download_name=f"{audio_token}.flac",
                mimetype='audio/flac'
            )
            response.call_on_close(remove_file_after_send)
            return response
        else:
            logger.error(f"Audio file not found: {audio_token}.flac")
            return jsonify({"error": "Audio file not found"}), 404

    except Exception as e:
        logger.error(f"HTTP download error for {audio_token}: {e}")
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@http_app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "service": "audio_download"}), 200


def start_http_server():
    """Start HTTP server for audio downloads"""
    global http_server
    try:
        logger.info(f"Starting HTTP server on port {HTTP_PORT}")
        http_server = Thread(
            target=lambda: http_app.run(
                host='0.0.0.0',
                port=HTTP_PORT,
                debug=False,
                use_reloader=False,
                threaded=True
            ),
            daemon=True
        )
        http_server.start()
        logger.info(f"HTTP server started successfully on port {HTTP_PORT}")
        return True
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        return False
###---HTTP server code END---####


def main():
    """Main application"""
    global pipeline, whisper_model, is_generating, is_recording, conversation_history

    logger.info("=== WebSocket TTS/STT Server Starting ===")

    # Create directories
    os.makedirs(DEFAULT_SAVE_PATH, exist_ok=True)
    os.makedirs('./logs', exist_ok=True)

    layout = create_layout()
    # ONLY ADDITION: enable_close_attempted_event for proper exit handling
    window = sg.Window('WebSocket TTS/STT Server', layout, finalize=True, resizable=True, enable_close_attempted_event=True)

    # Load models
    logger.info("Loading models...")

    # Load Whisper
    if load_whisper_model():
        window['stt_model_status'].update("✅ Loaded", text_color='green')
        window['stt_record5'].update(disabled=False)
        window['stt_record10'].update(disabled=False)
    else:
        window['stt_model_status'].update("❌ Failed", text_color='red')

    # Load Kokoro
    if load_kokoro_model():
        window['tts_model_status'].update("✅ Loaded", text_color='green')
        window['tts_generate'].update(disabled=False)
        window['tts_generate_long'].update(disabled=False)
        update_tts_log(window, "[SUCCESS] Kokoro-82M ready for generation!")
    else:
        window['tts_model_status'].update("❌ Failed", text_color='red')
        update_tts_log(window, "[ERROR] Failed to load Kokoro model")

    # Auto-start HTTP server first
    logger.info("Auto-starting HTTP server...")
    if start_http_server():
        logger.info("HTTP server started successfully")
    else:
        logger.error("Failed to start HTTP server")
    # Start cleanup scheduler
    start_cleanup_scheduler()

    # Auto-start WebSocket server
    logger.info("Auto-starting WebSocket server...")
    try:
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_websocket_server(window))

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        window['ws_start'].update(disabled=True)
        window['ws_stop'].update(disabled=False)
        logger.info("WebSocket server auto-started")
    except Exception as e:
        logger.error(f"Failed to auto-start server: {e}")

    logger.info("Entering main event loop...")

    while True:
        event, values = window.read(timeout=100)

        # ONLY ADDITION: Handle close event properly
        if event in (sg.WIN_CLOSED, sg.WIN_CLOSE_ATTEMPTED_EVENT, 'exit'):
            break

        # STT Events
        elif event == 'stt_record5' and whisper_model and not is_recording:
            thread = threading.Thread(target=record_audio_stt, args=(5, window), daemon=True)
            thread.start()

        elif event == 'stt_record10' and whisper_model and not is_recording:
            thread = threading.Thread(target=record_audio_stt, args=(10, window), daemon=True)
            thread.start()

        elif event == 'stt_stop':
            is_recording = False

        elif event == 'stt_clear':
            window['stt_output'].update('')
            window['stt_language'].update('Unknown')
            window['stt_status'].update('Ready')

        elif event == 'stt_test_mic':
            test_microphone()

        # TTS Events
        elif event in ['tts_generate', 'tts_generate_long'] and pipeline and not is_generating:
            text = values['tts_text'].strip()
            if not text:
                sg.popup_error("Enter text to generate!")
                continue

            voice = values['tts_voice']
            save_path = values['tts_save_path']
            filename_prefix = values['tts_filename_prefix']
            add_timestamp = values['tts_add_timestamp']

            thread = threading.Thread(
                target=generate_speech_kokoro,
                args=(text, voice, save_path, filename_prefix, add_timestamp, window),
                daemon=True
            )
            thread.start()

        elif event == 'tts_play':
            audio_file = window['tts_audio_file'].get()
            if audio_file and audio_file != 'None':
                play_audio(audio_file, window)
            else:
                sg.popup_error("No audio to play!")

        elif event == 'tts_stop_audio':
            stop_audio(window)

        elif event == 'tts_save':
            audio_file = window['tts_audio_file'].get()
            if audio_file and audio_file != 'None':
                save_path = sg.popup_get_file('Save Copy As', save_as=True, file_types=(("WAV Files", "*.wav"),))
                if save_path:
                    shutil.copy2(audio_file, save_path)
                    sg.popup(f"Copied to: {save_path}")

        elif event == 'tts_clear_history':
            conversation_history.clear()
            window['tts_history'].update([])

        # WebSocket Events
        elif event == 'ws_start':
            if not server_running:
                try:
                    def run_server():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(start_websocket_server(window))

                    server_thread = threading.Thread(target=run_server, daemon=True)
                    server_thread.start()

                    window['ws_start'].update(disabled=True)
                    window['ws_stop'].update(disabled=False)
                except Exception as e:
                    sg.popup_error(f"Failed to start server: {e}")

        elif event == 'ws_stop':
            stop_websocket_server(window)
            window['ws_start'].update(disabled=False)
            window['ws_stop'].update(disabled=True)

        elif event == 'ws_clear_log':
            window['ws_log'].update('')

    # ONLY ADDITION: Cleanup on exit
    logger.info("Shutting down...")
    if server_running:
        stop_websocket_server(window)

    try:
        window.close()
    except:
        pass

    logger.info("=== WebSocket TTS/STT Server Shutdown Complete ===")

if __name__ == "__main__":
    main()