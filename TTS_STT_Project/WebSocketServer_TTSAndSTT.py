####Insert your PySimpleGUI distribution key at the top
PySimpleGUI_License ="""elyIJgMoaqWzNll5bHnuNAlhVaHhlKwCZhSlIj6KI6kpRep6cU3SRPyNafW3JZ1PdsGclzv8bAiLIBsZI7kVxEp5Y42cVRuQc822VnJARuCeIO6RMaTUcWzKNbzlIdz8NojQchxsNoSdwtivTJGQlljeZvWq56z0ZhUGRalYceGsx8vYerWN1hlQbZn2RxWkZMXNJZzOa1WH9BuVIFjLoGipNuSi4XwpIgimwkirTYmaFitOZaUcZ4pdc8n1N602Iljyoai5ScmVFnntYWWZ50uZYeXWROosIXikwrirTEmOFBtHZNUNxHhlch3uQRi5O8iXJ9C8Z2WHhLlScjmdEei1LRCkJ8DYbm2R1mwfYpWq5g5iIXjuoNiIS4mFFdnDYDW65zukYSXxR5oZIEEOJqlEavGZVeyxYiS8IHs8I0kwN71qcY3lRPvIbPWIVByOSKUnQGiQOpihIhy8M6DIUK1bM8i3ImsYITkvRHhPdnG8VoJfc63LNu1KZVWsQ3iTOgiGIJybM1D7Iy1bLeTdAux4LgTREe5pIwipwoiXRiG6FM0QZWUoVg4EcNGHlFyGZUXMMLi0OniBIZyqMIDVIs1jLdTBAu1uLeTVEo0lIFiFwXiVRuW61EhXaLWBxFB7Z1GYRly0ZFXFNkzvI6jqoqiHaFmTFon7YMWT5buOYsXNRiozYlmZVgo2Z0X3J5hYMZzFMOzeMQ09BfnvbxWNFtpxbuCR52jZbv2X05ikL1CzJkJWUwEFF9kxZyHWJ4lTc03CMbiXOkicID0PNxSo4C5yMHCn4gymMMj7ITuAMhT0Q83WIQnX0d=J517c7d5fae65077acdc2471d2e926436011f50cc3bff5e606996187bbc87cb0a4796f69a65646f4f2401c26398c4df3c2e20ac1bdeb726222b3535af30177dbcda327d862b8ef3d121801906e44ce44ce74e02331e3f88e13586c3337e7d4b113f826187ea2a355b3075917c78aa05926b289cf8738a54267aa4915a7f14840a36d4d4abc646871adbb8d9bf078f67f1e8461fde9cf36a2a5def3e81ce135a48eeb90c5d39a04e85af461d99f296a8677f30403585d5bb3eb9bec197839c48f1e4365fa61bd8b798a73e11b4c5de4285f3bfcb92434865cc97c01064fa2da9241ae20be5d353e47db24a67d0458bf8b95b51226ad2e3cefacb628e38d343183a672022e4bec60007d2004e040f64d7f5dc4cfdc95e1676717fb7ac0cfdff6f5ce5426003db19b59a1407e89b7d3aff88592a0d6d26b7dc3c2dc5903fa3bf2ffa6a3ffb6991ae1a89e4a24e215401673b9fad941e4b142a751654c7028d616835a554764579e316a98f22eabad4f98395c807633d28f9372488dcc39702c95545a413b990146c6d9b9030e18709d2c10fbe7d8510a81e9088349ea5a870a51e5d3cda58754b22e686394e3ecc5a43e47a6d4e374fc1972f7e95be48c7863a51de076112dd2415591c2c2851ddbf12c91de33d4e2aa28c8418c59c70a5dcd523cbc7df76ca12fd4e50be0cde747ebe6b43f21821190ed58faf2a6e416850145b10"""

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
            window['stt_status'].update("📄 Transcribing...")
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
            '📄', '[LOADING]')
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
            window['tts_status'].update(f"Generated: {filename}")
            window['tts_gen_time'].update(f"{generation_time:.2f}s")
            window['tts_audio_duration'].update(f"{audio_duration:.2f}s")
            window['tts_history'].update(conversation_history[-10:])

            update_tts_log(window, f"[SUCCESS] Generated {audio_duration:.2f}s audio in {generation_time:.2f}s")
            return output_file

    except Exception as e:
        error_msg = f"[ERROR] Generation error: {e}"
        window['tts_status'].update(error_msg)
        update_tts_log(window, error_msg)
        return None
    finally:
        is_generating = False
        window['tts_generate'].update(disabled=False)
        window['tts_generate_long'].update(disabled=False)


def play_audio(file_path, window):
    """Play audio file"""
    try:
        if os.path.exists(file_path):
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            update_tts_log(window, f"Playing: {os.path.basename(file_path)}")
        else:
            sg.popup_error("Audio file not found!")
    except Exception as e:
        sg.popup_error(f"Playback error: {e}")


def stop_audio(window):
    """Stop audio playback"""
    try:
        pygame.mixer.music.stop()
        update_tts_log(window, "Audio stopped")
    except Exception as e:
        update_tts_log(window, f"[ERROR] Stop error: {e}")


async def handle_websocket_connection(websocket, path, window):
    """Handle WebSocket connections"""
    try:
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        # Update GUI log
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

                    # Visual feedback in TTS tab
                    window['tts_text'].update(text)
                    window['tts_voice'].update(voice)
                    window['tts_status'].update("🌐 Processing WebSocket TTS request...")

                    update_gui_log(f"TTS request: {text[:50]}...")

                    if pipeline:
                        # Generate audio (same as before)
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

                            # Convert to bytes
                            buffer = io.BytesIO()
                            sf.write(buffer, full_audio, 24000, format='WAV')
                            audio_b64 = base64.b64encode(buffer.getvalue()).decode()

                            response = {
                                'type': 'tts_response',
                                'audio': audio_b64,
                                'voice': voice
                            }
                            await websocket.send(json.dumps(response))

                            window['tts_status'].update("✅ WebSocket TTS completed")
                            update_gui_log("TTS response sent")
                        else:
                            await websocket.send(json.dumps({'type': 'error', 'message': 'Audio generation failed'}))
                            window['tts_status'].update("❌ TTS generation failed")
                    else:
                        await websocket.send(json.dumps({'type': 'error', 'message': 'Kokoro model not loaded'}))

                elif request_type == 'stt':
                    audio_b64 = data.get('audio')

                    # Visual feedback in STT tab
                    window['stt_status'].update("🌐 Processing WebSocket STT request...")

                    update_gui_log("STT request received")

                    if audio_b64 and whisper_model:
                        try:
                            # Decode audio properly using soundfile
                            audio_bytes = base64.b64decode(audio_b64)
                            audio_buffer = io.BytesIO(audio_bytes)
                            audio_array, sample_rate = sf.read(audio_buffer)

                            # Ensure mono audio
                            if len(audio_array.shape) > 1:
                                audio_array = audio_array.mean(axis=1)

                            # Convert to float32 (critical for Whisper)
                            audio_array = audio_array.astype(np.float32)

                            result = whisper_model.transcribe(audio_array)

                            # Show result in STT tab
                            window['stt_output'].update(result['text'])
                            window['stt_language'].update(f"Language: {result['language']}")
                            window['stt_status'].update("✅ WebSocket STT completed")

                            response = {
                                'type': 'stt_response',
                                'text': result['text'],
                                'language': result['language']
                            }
                            await websocket.send(json.dumps(response))
                            update_gui_log(f"STT response: {result['text'][:50]}...")

                        except Exception as stt_error:
                            error_msg = f"STT processing error: {str(stt_error)}"
                            await websocket.send(json.dumps({'type': 'error', 'message': error_msg}))
                            window['stt_status'].update("❌ STT processing failed")
                            update_gui_log(error_msg)
                            logger.error(f"STT error: {stt_error}")
                    else:
                        await websocket.send(json.dumps({'type': 'error', 'message': 'Whisper model not loaded'}))
                        window['stt_status'].update("❌ STT processing failed")
            except json.JSONDecodeError:
                await websocket.send(json.dumps({'type': 'error', 'message': 'Invalid JSON'}))
            except Exception as e:
                await websocket.send(json.dumps({'type': 'error', 'message': str(e)}))
                logger.error(f"WebSocket handler error: {e}")

    except websockets.exceptions.ConnectionClosed:
        update_gui_log(f"Client disconnected: {client_info}")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")


async def start_websocket_server(window):
    """Start WebSocket server"""
    global websocket_server, server_running

    try:
        async def handler(websocket):
            await handle_websocket_connection(websocket, None, window)

        websocket_server = await websockets.serve(
            handler,
            WEBSOCKET_HOST,
            WEBSOCKET_PORT
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
        [sg.Text('Endpoints:')],
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


def main():
    """Main application"""
    global pipeline, whisper_model, is_generating, is_recording, conversation_history

    logger.info("=== WebSocket TTS/STT Server Starting ===")

    # Create directories
    os.makedirs(DEFAULT_SAVE_PATH, exist_ok=True)
    os.makedirs('./logs', exist_ok=True)

    layout = create_layout()
    window = sg.Window('WebSocket TTS/STT Server', layout, finalize=True, resizable=True)

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

    # Variables for async server
    server_task = None
    loop = None

    logger.info("Entering main event loop...")

    while True:
        event, values = window.read(timeout=100)

        if event in (sg.WIN_CLOSED, 'exit'):
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

    # Cleanup
    if server_running:
        stop_websocket_server(window)

    window.close()
    logger.info("=== WebSocket TTS/STT Server Shutdown Complete ===")


if __name__ == "__main__":
    main()