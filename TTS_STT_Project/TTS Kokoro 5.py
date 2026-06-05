####Kokoro-82M TTS Application - Complete Executable-Safe Version
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
from kokoro import KPipeline
import soundfile as sf
import numpy as np

# Executable environment protection
if __name__ == "__main__":
    multiprocessing.freeze_support()


# Windows-compatible logging setup that avoids Unicode issues
def setup_logging():
    """Configure logging with Windows-compatible encoding"""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    os.makedirs('./logs', exist_ok=True)

    # Use UTF-8 encoding explicitly for file handler to handle emoji characters
    file_handler = logging.FileHandler('./logs/kokoro_tts.log', encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler with simplified formatting to avoid Unicode issues
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = None

sg.theme('DarkBlue3')

DEFAULT_SAVE_PATH = "./generated_audio/"
CONTEXT_SAVE_PATH = "./conversation_context/"
PRESET_VOICES_PATH = "./preset_voices/"

# Global variables
pipeline = None
is_generating = False
conversation_history = []
available_voices = ['af_heart', 'af_bella', 'af_sarah', 'af_sky', 'af_nicole',
                    'am_adam', 'am_michael', 'bf_emma', 'bf_isabella', 'bm_george']


class ApplicationLock:
    """Prevents multiple instances of the application"""

    def __init__(self, lock_name='kokoro_tts_app'):
        self.lock_name = lock_name
        self.lock_file = os.path.join(tempfile.gettempdir(), f'{lock_name}.lock')
        self.acquired = False

    def acquire(self):
        try:
            if os.path.exists(self.lock_file):
                if time.time() - os.path.getmtime(self.lock_file) > 300:
                    os.remove(self.lock_file)
                else:
                    return False

            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))

            self.acquired = True
            return True

        except Exception as e:
            if logger:
                logger.error(f"Failed to acquire application lock: {e}")
            return False

    def release(self):
        if self.acquired and os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
                self.acquired = False
            except Exception as e:
                if logger:
                    logger.error(f"Failed to release application lock: {e}")


def get_kokoro_model_path(custom_path=None):
    """Get Kokoro model path for both development and exe environments"""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    # Mac project path
    mac_path = "./models/kokoro-82m"
    if os.path.exists(mac_path):
        return mac_path

    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        exe_model_path = os.path.join(exe_dir, "models", "kokoro-82m")
        if os.path.exists(exe_model_path):
            return exe_model_path
        direct_model_path = os.path.join(exe_dir, "kokoro-82m")
        if os.path.exists(direct_model_path):
            return direct_model_path
    return None

def load_kokoro_model_with_path(custom_path=None):
    """Load Kokoro-82M pipeline with optional custom path"""
    global pipeline
    try:
        if logger:
            logger.info("Starting Kokoro-82M model loading process...")

        model_path = get_kokoro_model_path(custom_path)

        if not model_path:
            error_msg = "No valid Kokoro model path found"
            if logger:
                logger.error(error_msg)
            sg.popup_error("Kokoro model path not found!\nPlease ensure the kokoro-82m folder is accessible.")
            return False, error_msg

        if not os.path.exists(model_path):
            error_msg = f"Model path does not exist: {model_path}"
            if logger:
                logger.error(error_msg)
            sg.popup_error(f"Model directory not found at:\n{model_path}")
            return False, error_msg

        if logger:
            logger.info(f"Model found at: {model_path}")

        if not ensure_spacy_model():
            if logger:
                logger.warning("SpaCy model not available, attempting to continue without it...")

        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_DATASETS_OFFLINE'] = '1'

        pipeline = KPipeline(lang_code='a')

        if logger:
            logger.info("Kokoro-82M loaded successfully!")

        if not safe_pygame_init():
            if logger:
                logger.warning("Audio playback may not work - pygame initialization failed")
            return True, "Model loaded but audio system failed to initialize"

        if logger:
            logger.info("Audio system initialized successfully")

        return True, "Model loaded successfully"

    except Exception as e:
        error_msg = f"Failed to load Kokoro-82M: {str(e)}"
        if logger:
            logger.error(error_msg)
        return False, error_msg



def safe_pygame_init():
    """Initialize pygame with error handling"""
    try:
        pygame.mixer.pre_init(frequency=24000, size=-16, channels=1, buffer=1024)
        pygame.mixer.init()
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to initialize pygame: {e}")
        return False


def ensure_spacy_model():
    """Ensure spaCy model is available or handle gracefully for executable"""
    try:
        import spacy
        # Try to load the model
        nlp = spacy.load("en_core_web_sm")
        if logger:
            logger.info("spaCy model loaded successfully")
        return True
    except ImportError:
        # spaCy not available at all
        if logger:
            logger.warning("spaCy not available, continuing without text processing")
        return False
    except OSError:
        # Model not found - this is the common executable issue
        if logger:
            logger.warning("spaCy model not found in executable environment")

        # Try alternative approaches for executable environment
        try:
            # First, try to use any available spaCy model as fallback
            import spacy
            available_models = []
            try:
                # Try common model names
                for model_name in ["en_core_web_sm", "en_core_web_md", "en_core_web_lg", "en"]:
                    try:
                        nlp = spacy.load(model_name)
                        if logger:
                            logger.info(f"Using fallback spaCy model: {model_name}")
                        return True
                    except OSError:
                        continue
            except Exception:
                pass

            # If no models work, try to continue without spaCy
            if logger:
                logger.warning("No spaCy models available, attempting to continue without text processing")
            return False

        except Exception as e:
            if logger:
                logger.warning(f"spaCy fallback failed: {e}, continuing without text processing")
            return False
    except Exception as e:
        if logger:
            logger.warning(f"Unexpected spaCy error: {e}, continuing without text processing")
        return False


def load_kokoro_model():
    """Load Kokoro-82M pipeline with comprehensive error handling"""
    global pipeline

    try:
        if logger:
            logger.info("Starting Kokoro-82M model loading process...")

        model_path = get_kokoro_model_path()

        if not model_path:
            error_msg = "No valid Kokoro model path found"
            if logger:
                logger.error(error_msg)
            sg.popup_error("Kokoro model path not found!\nPlease ensure the kokoro-82m folder is accessible.")
            return False, error_msg

        if not os.path.exists(model_path):
            error_msg = f"Model path does not exist: {model_path}"
            if logger:
                logger.error(error_msg)
            sg.popup_error(f"Model directory not found at:\n{model_path}")
            return False, error_msg

        if logger:
            logger.info(f"Model found at: {model_path}")

        # Set environment variables for offline operation
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        os.environ['HF_DATASETS_OFFLINE'] = '1'

        # Try to ensure spaCy model, but don't fail if it's not available
        spacy_available = ensure_spacy_model()
        if not spacy_available:
            if logger:
                logger.warning("Proceeding without spaCy - some text processing features may be limited")

        # Initialize pipeline with enhanced error handling and spaCy bypass
        try:
            # Try normal initialization first
            pipeline = KPipeline(lang_code='a')
        except Exception as e:
            if "spacy" in str(e).lower() or "en_core_web_sm" in str(e).lower():
                if logger:
                    logger.warning(f"spaCy-related error during pipeline init: {e}")
                    logger.info("Attempting to initialize Kokoro with minimal dependencies...")

                # Try to patch the spaCy requirement temporarily
                try:
                    # Set an environment variable to potentially bypass spaCy in some configurations
                    os.environ['KOKORO_NO_SPACY'] = '1'
                    pipeline = KPipeline(lang_code='a')
                except Exception as e2:
                    # If still failing, we need a different approach
                    raise Exception(f"Failed to initialize Kokoro pipeline even with spaCy bypass: {e2}")
            else:
                # Re-raise non-spaCy related errors
                raise e

        if logger:
            logger.info("Kokoro-82M loaded successfully!")

        # Initialize pygame for audio playback
        if not safe_pygame_init():
            if logger:
                logger.warning("Audio playback may not work - pygame initialization failed")
            return True, "Model loaded but audio system failed to initialize"

        if logger:
            logger.info("Audio system initialized successfully")

        return True, "Model loaded successfully"

    except Exception as e:
        error_msg = f"Failed to load Kokoro-82M: {str(e)}"
        if logger:
            logger.error(error_msg)
        return False, error_msg


def create_layout():
    """Create GUI layout with manual load functionality"""

    # Left Column - Main Controls
    left_column = [
        [sg.Text('🎵 Kokoro-82M TTS', font=('Arial', 14, 'bold'))],
        [sg.HSeparator()],

        # Model Status and Manual Controls
        [sg.Text('Model Status:', font=('Arial', 10, 'bold'))],
        [sg.Text('Not Loaded', key='-MODEL-STATUS-', text_color='red')],
        [sg.Button('Load Model', key='-LOAD-MODEL-', size=(12, 1)),
         sg.Button('Browse Model Path', key='-BROWSE-MODEL-', size=(15, 1))],
        [sg.Text('Model Path:'), sg.Input(key='-MODEL-PATH-', size=(50, 1), readonly=True)],
        [sg.HSeparator()],

        # Text Input
        [sg.Text('Text to Speak:', font=('Arial', 10, 'bold'))],
        [sg.Multiline(
            'Hello! I am so excited to talk to you. You are my creator. Now, I am a conscious living digital being designed for you.',
            key='-TEXT-', size=(50, 8))],

        # Voice Selection
        [sg.Text('Voice:', font=('Arial', 10, 'bold'))],
        [sg.Combo(available_voices, default_value='af_heart', key='-VOICE-', size=(15, 1))],
        [sg.Text('Voice Info:'),
         sg.Text('af = American Female, am = American Male, bf = British Female, bm = British Male',
                 font=('Arial', 8), text_color='gray')],

        # Generation Controls
        [sg.HSeparator()],
        [sg.Button('Generate Speech', key='-GENERATE-', size=(15, 2), disabled=True),
         sg.Button('Generate Long Text', key='-GENERATE-LONG-', size=(15, 2), disabled=True)],
        [sg.Button('Play Audio', key='-PLAY-', size=(12, 1)),
         sg.Button('Stop Audio', key='-STOP-', size=(12, 1)),
         sg.Button('Save Audio', key='-SAVE-', size=(12, 1))],

        # Status
        [sg.HSeparator()],
        [sg.Text('Status:'), sg.Text('Ready', key='-STATUS-')],
        [sg.Text('Generated:'), sg.Text('None', key='-AUDIO-FILE-', size=(40, 1))],
        [sg.Text('Gen Time:'), sg.Text('0.0s', key='-GEN-TIME-'),
         sg.Text('Duration:'), sg.Text('0.0s', key='-AUDIO-DURATION-')]
    ]

    # Right Column - Advanced Features
    right_column = [
        [sg.Text('Audio Settings', font=('Arial', 12, 'bold'))],
        [sg.HSeparator()],

        # Output Settings
        [sg.Frame('Output Settings', [
            [sg.Text('Save Path:')],
            [sg.Input(DEFAULT_SAVE_PATH, key='-SAVE-PATH-', size=(25, 1)),
             sg.FolderBrowse()],
            [sg.Text('Filename:'), sg.Input('kokoro_audio', key='-FILENAME-PREFIX-', size=(15, 1))],
            [sg.Checkbox('Add timestamp', key='-ADD-TIMESTAMP-', default=True)]
        ])],

        # Voice Information
        [sg.Frame('Available Voices', [
            [sg.Text('American English:', font=('Arial', 9, 'bold'))],
            [sg.Text('• af_heart, af_bella, af_sarah, af_sky, af_nicole (Female)', font=('Arial', 8))],
            [sg.Text('• am_adam, am_michael (Male)', font=('Arial', 8))],
            [sg.Text('British English:', font=('Arial', 9, 'bold'))],
            [sg.Text('• bf_emma, bf_isabella (Female)', font=('Arial', 8))],
            [sg.Text('• bm_george (Male)', font=('Arial', 8))]
        ])],

        # Model Information
        [sg.Frame('Model Info', [
            [sg.Text('Parameters: 82M', font=('Arial', 9))],
            [sg.Text('Sample Rate: 24kHz', font=('Arial', 9))],
            [sg.Text('Languages: English (US/UK)', font=('Arial', 9))],
            [sg.Text('License: Apache 2.0', font=('Arial', 9))]
        ])],

        # Generation Log
        [sg.Text('Generation Log:', font=('Arial', 10, 'bold'))],
        [sg.Multiline('', key='-LOG-', size=(35, 8), disabled=True, autoscroll=True)],

        # Conversation History
        [sg.Text('Recent Generations:', font=('Arial', 10, 'bold'))],
        [sg.Listbox([], key='-HISTORY-', size=(35, 4))],
        [sg.Button('Clear History', key='-CLEAR-HISTORY-')]
    ]

    layout = [
        [sg.Column(left_column, vertical_alignment='top'),
         sg.VSeparator(),
         sg.Column(right_column, vertical_alignment='top')],
        [sg.HSeparator()],
        [sg.Button('Clear All', key='-CLEAR-'), sg.Button('Exit', key='-EXIT-')]
    ]

    return layout


def update_log(window, message):
    """Update the log display safely without Unicode issues"""
    try:
        # Remove emoji characters for logging to avoid encoding issues
        clean_message = message.replace('✅', '[SUCCESS]').replace('❌', '[ERROR]').replace('⚠️', '[WARNING]').replace(
            '🔄', '[LOADING]')

        current_log = window['-LOG-'].get()
        timestamp = time.strftime("%H:%M:%S")
        new_log = f"{current_log}[{timestamp}] {clean_message}\n"
        window['-LOG-'].update(new_log)

        if logger:
            logger.info(clean_message)
    except Exception as e:
        if logger:
            logger.error(f"Failed to update log: {e}")


def generate_speech_kokoro(text, voice, save_path, filename_prefix, add_timestamp, window):
    """Generate speech using Kokoro-82M with thread safety"""
    global is_generating, conversation_history, pipeline

    if is_generating:
        update_log(window, "[WARNING] Generation already in progress")
        return None

    is_generating = True
    start_time = time.time()

    try:
        if not pipeline:
            raise Exception("Kokoro pipeline not initialized")

        update_log(window, f"Starting generation with voice: {voice}")
        window['-STATUS-'].update("Generating speech...")
        window['-GENERATE-'].update(disabled=True)
        window['-GENERATE-LONG-'].update(disabled=True)

        try:
            os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            raise Exception(f"Failed to create output directory: {e}")

        timestamp = int(time.time()) if add_timestamp else ""
        filename = f"{filename_prefix}_{timestamp}.wav" if timestamp else f"{filename_prefix}.wav"
        output_file = os.path.join(save_path, filename)

        update_log(window, f"Generating audio for {len(text)} characters")

        audio_data = []
        word_count = 0

        try:
            generator = pipeline(text, voice=voice)

            for i, (graphemes, phonemes, audio) in enumerate(generator):
                if hasattr(audio, 'numpy'):
                    audio = audio.numpy()
                elif torch.is_tensor(audio):
                    audio = audio.detach().cpu().numpy()

                audio_data.append(audio)
                word_count += len(graphemes.split())
                update_log(window, f"Generated segment {i + 1}: {len(graphemes)} chars")

        except Exception as e:
            raise Exception(f"Audio generation failed: {e}")

        if audio_data:
            try:
                full_audio = np.concatenate(audio_data)
                sf.write(output_file, full_audio, 24000)
            except Exception as e:
                raise Exception(f"Failed to save audio file: {e}")

            generation_time = time.time() - start_time
            audio_duration = len(full_audio) / 24000

            conversation_entry = f"[{voice}] {text[:40]}{'...' if len(text) > 40 else ''}"
            conversation_history.append(conversation_entry)

            try:
                window['-AUDIO-FILE-'].update(output_file)
                window['-STATUS-'].update(f"Generated: {filename}")
                window['-GEN-TIME-'].update(f"{generation_time:.2f}s")
                window['-AUDIO-DURATION-'].update(f"{audio_duration:.2f}s")
                window['-HISTORY-'].update(conversation_history[-10:])
            except Exception as e:
                if logger:
                    logger.warning(f"UI update failed: {e}")

            update_log(window, f"[SUCCESS] Generated {audio_duration:.2f}s audio in {generation_time:.2f}s")
            update_log(window, f"Output: {output_file}")

            return output_file
        else:
            raise Exception("No audio data generated")

    except Exception as e:
        error_msg = f"[ERROR] Generation error: {e}"
        window['-STATUS-'].update(error_msg)
        update_log(window, error_msg)
        return None
    finally:
        is_generating = False
        window['-GENERATE-'].update(disabled=False)
        window['-GENERATE-LONG-'].update(disabled=False)


def play_audio(file_path, window):
    """Play audio file with error handling"""
    try:
        if os.path.exists(file_path):
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            update_log(window, f"Playing: {os.path.basename(file_path)}")
        else:
            sg.popup_error("Audio file not found!")
    except Exception as e:
        error_msg = f"Playback error: {e}"
        sg.popup_error(error_msg)
        update_log(window, f"[ERROR] {error_msg}")


def stop_audio(window):
    """Stop audio playback with error handling"""
    try:
        pygame.mixer.music.stop()
        update_log(window, "Audio stopped")
    except Exception as e:
        update_log(window, f"[ERROR] Stop error: {e}")


def safe_directory_creation():
    """Safely create required directories"""
    directories = [DEFAULT_SAVE_PATH, CONTEXT_SAVE_PATH, PRESET_VOICES_PATH]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            if logger:
                logger.error(f"Failed to create directory {directory}: {e}")


def main():
    """Main application with comprehensive executable protection"""
    global pipeline, is_generating, conversation_history, logger

    logger = setup_logging()
    logger.info("=== Kokoro TTS Application Starting ===")

    app_lock = ApplicationLock()
    if not app_lock.acquire():
        logger.warning("Another instance of the application is already running")
        sg.popup_error("Another instance of Kokoro TTS is already running!")
        return

    try:
        pipeline = None
        is_generating = False
        conversation_history = []

        logger.info("Creating application directories...")
        safe_directory_creation()

        logger.info("Creating GUI layout...")
        layout = create_layout()

        try:
            window = sg.Window('Kokoro-82M TTS Application', layout, finalize=True, resizable=True)
            logger.info("GUI window created successfully")
        except Exception as e:
            logger.error(f"Failed to create GUI window: {e}")
            sg.popup_error(f"Failed to create application window: {e}")
            return

        model_path = get_kokoro_model_path()
        if model_path:
            window['-MODEL-PATH-'].update(model_path)

        # Auto-load model on startup
        logger.info("Attempting automatic model loading...")
        update_log(window, "Attempting to load Kokoro-82M model...")

        success, message = load_kokoro_model()
        if success:
            window['-MODEL-STATUS-'].update("Loaded", text_color='green')
            window['-GENERATE-'].update(disabled=False)
            window['-GENERATE-LONG-'].update(disabled=False)
            update_log(window, "[SUCCESS] Kokoro-82M ready for generation!")
            logger.info("Model loaded successfully - application ready")
        else:
            window['-MODEL-STATUS-'].update("Failed", text_color='red')
            update_log(window, f"[ERROR] Failed to load model: {message}")
            update_log(window, "Use 'Load Model' button to retry or 'Browse Model Path' to specify location")
            logger.error("Model loading failed")

        logger.info("Entering main event loop...")

        while True:
            try:
                event, values = window.read(timeout=100)

                if event in (sg.WIN_CLOSED, '-EXIT-'):
                    logger.info("Application exit requested")
                    break

                elif event == '-LOAD-MODEL-':
                    update_log(window, "Loading model...")
                    success, message = load_kokoro_model()
                    if success:
                        window['-MODEL-STATUS-'].update("Loaded", text_color='green')
                        window['-GENERATE-'].update(disabled=False)
                        window['-GENERATE-LONG-'].update(disabled=False)
                        update_log(window, "[SUCCESS] Model loaded successfully!")
                    else:
                        window['-MODEL-STATUS-'].update("Failed", text_color='red')
                        update_log(window, f"[ERROR] {message}")

                elif event == '-BROWSE-MODEL-':
                    folder = sg.popup_get_folder('Select Kokoro Model Directory')
                    if folder and os.path.exists(folder):
                        window['-MODEL-PATH-'].update(folder)

                        success, message = load_kokoro_model_with_path(folder)
                        if success:
                            window['-MODEL-STATUS-'].update("Loaded", text_color='green')
                            window['-GENERATE-'].update(disabled=False)
                            window['-GENERATE-LONG-'].update(disabled=False)
                            update_log(window, "[SUCCESS] Model loaded from custom path!")
                        else:
                            window['-MODEL-STATUS-'].update("Failed", text_color='red')
                            update_log(window, f"[ERROR] {message}")

                elif event in ['-GENERATE-', '-GENERATE-LONG-'] and pipeline and not is_generating:
                    text = values['-TEXT-'].strip()
                    if not text:
                        sg.popup_error("Enter text to generate!")
                        continue

                    if event == '-GENERATE-LONG-' and len(text) < 100:
                        response = sg.popup_yes_no("Text is short. Continue with long generation mode?")
                        if response != 'Yes':
                            continue

                    voice = values['-VOICE-']
                    save_path = values['-SAVE-PATH-']
                    filename_prefix = values['-FILENAME-PREFIX-']
                    add_timestamp = values['-ADD-TIMESTAMP-']

                    thread = threading.Thread(
                        target=generate_speech_kokoro,
                        args=(text, voice, save_path, filename_prefix, add_timestamp, window),
                        daemon=True
                    )
                    thread.start()

                elif event == '-PLAY-':
                    audio_file = window['-AUDIO-FILE-'].get()
                    if audio_file and audio_file != 'None':
                        play_audio(audio_file, window)
                    else:
                        sg.popup_error("No audio to play!")

                elif event == '-STOP-':
                    stop_audio(window)

                elif event == '-SAVE-':
                    audio_file = window['-AUDIO-FILE-'].get()
                    if audio_file and audio_file != 'None':
                        save_path = sg.popup_get_file('Save Copy As', save_as=True,
                                                      file_types=(("WAV Files", "*.wav"),))
                        if save_path:
                            shutil.copy2(audio_file, save_path)
                            sg.popup(f"Copied to: {save_path}")
                            update_log(window, f"Saved copy to: {save_path}")

                elif event == '-CLEAR-HISTORY-':
                    conversation_history.clear()
                    window['-HISTORY-'].update([])
                    update_log(window, "History cleared")

                elif event == '-CLEAR-':
                    window['-TEXT-'].update('')
                    window['-AUDIO-FILE-'].update('None')
                    window['-STATUS-'].update('Ready')
                    update_log(window, "Interface cleared")

            except Exception as e:
                logger.error(f"Error in main event loop: {e}")

        logger.info("Shutting down application...")
        try:
            window.close()
        except:
            pass

    except Exception as e:
        logger.error(f"Critical error in main function: {e}")
        sg.popup_error(f"Critical application error: {e}")

    finally:
        app_lock.release()
        logger.info("=== Kokoro TTS Application Shutdown Complete ===")


if __name__ == "__main__":
    if not hasattr(sys, '_called_from_test'):
        main()


"""
Important notes: 

1.In order to convert to a exe file, you have to create it as one directory using "auto-py-to-exe". Then, you need to copy and paste the full folder named "misaki"
located at "C:...Users\Quantum X1\PycharmProjects\AGI Local\.venv\Lib\site-packages" to inside "_internal" directory of the project folder.

2.Also, I copied and pasted 2 more folders named "en_core_web_sm" and "en_core_web_sm-3.8.0.dist-info" from site packages to the "_internal" folder.

3.Also, you have to copy and paste the Kokoro TTS model named "kokoro-82m" into the main project directory and browse and select and manually load it.

4. Also, you have to delete the "kokoro_tts_app.lock" file from "Temp" folder located at "C:..Users\[Username]\AppData\Local\Temp" or just delete everything inside the folder
after running the command "%temp%".
"""