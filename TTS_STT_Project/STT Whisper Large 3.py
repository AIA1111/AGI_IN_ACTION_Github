####Insert your PySimpleGUI distribution key at the top
PySimpleGUI_License ="""elyIJgMoaqWzNll5bHnuNAlhVaHhlKwCZhSlIj6KI6kpRep6cU3SRPyNafW3JZ1PdsGclzv8bAiLIBsZI7kVxEp5Y42cVRuQc822VnJARuCeIO6RMaTUcWzKNbzlIdz8NojQchxsNoSdwtivTJGQlljeZvWq56z0ZhUGRalYceGsx8vYerWN1hlQbZn2RxWkZMXNJZzOa1WH9BuVIFjLoGipNuSi4XwpIgimwkirTYmaFitOZaUcZ4pdc8n1N602Iljyoai5ScmVFnntYWWZ50uZYeXWROosIXikwrirTEmOFBtHZNUNxHhlch3uQRi5O8iXJ9C8Z2WHhLlScjmdEei1LRCkJ8DYbm2R1mwfYpWq5g5iIXjuoNiIS4mFFdnDYDW65zukYSXxR5oZIEEOJqlEavGZVeyxYiS8IHs8I0kwN71qcY3lRPvIbPWIVByOSKUnQGiQOpihIhy8M6DIUK1bM8i3ImsYITkvRHhPdnG8VoJfc63LNu1KZVWsQ3iTOgiGIJybM1D7Iy1bLeTdAux4LgTREe5pIwipwoiXRiG6FM0QZWUoVg4EcNGHlFyGZUXMMLi0OniBIZyqMIDVIs1jLdTBAu1uLeTVEo0lIFiFwXiVRuW61EhXaLWBxFB7Z1GYRly0ZFXFNkzvI6jqoqiHaFmTFon7YMWT5buOYsXNRiozYlmZVgo2Z0X3J5hYMZzFMOzeMQ09BfnvbxWNFtpxbuCR52jZbv2X05ikL1CzJkJWUwEFF9kxZyHWJ4lTc03CMbiXOkicID0PNxSo4C5yMHCn4gymMMj7ITuAMhT0Q83WIQnX0d=J517c7d5fae65077acdc2471d2e926436011f50cc3bff5e606996187bbc87cb0a4796f69a65646f4f2401c26398c4df3c2e20ac1bdeb726222b3535af30177dbcda327d862b8ef3d121801906e44ce44ce74e02331e3f88e13586c3337e7d4b113f826187ea2a355b3075917c78aa05926b289cf8738a54267aa4915a7f14840a36d4d4abc646871adbb8d9bf078f67f1e8461fde9cf36a2a5def3e81ce135a48eeb90c5d39a04e85af461d99f296a8677f30403585d5bb3eb9bec197839c48f1e4365fa61bd8b798a73e11b4c5de4285f3bfcb92434865cc97c01064fa2da9241ae20be5d353e47db24a67d0458bf8b95b51226ad2e3cefacb628e38d343183a672022e4bec60007d2004e040f64d7f5dc4cfdc95e1676717fb7ac0cfdff6f5ce5426003db19b59a1407e89b7d3aff88592a0d6d26b7dc3c2dc5903fa3bf2ffa6a3ffb6991ae1a89e4a24e215401673b9fad941e4b142a751654c7028d616835a554764579e316a98f22eabad4f98395c807633d28f9372488dcc39702c95545a413b990146c6d9b9030e18709d2c10fbe7d8510a81e9088349ea5a870a51e5d3cda58754b22e686394e3ecc5a43e47a6d4e374fc1972f7e95be48c7863a51de076112dd2415591c2c2851ddbf12c91de33d4e2aa28c8418c59c70a5dcd523cbc7df76ca12fd4e50be0cde747ebe6b43f21821190ed58faf2a6e416850145b10"""

import PySimpleGUI as sg
import whisper
import pyaudio
import wave
import tempfile
import os
import threading
import time
import numpy as np
import sounddevice as sd

# GUI Theme
sg.theme('DarkBlue3')

# **CUSTOM MODEL PATH** - Change this to your desired location
CUSTOM_MODEL_PATH = "./models/whisper-large-v3/large-v3.pt"  # Your custom path
USE_CUSTOM_PATH = True  # Set to False to use cache

# Initialize Whisper
model = None
is_recording = False
audio_thread = None

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


def load_whisper_model():
    """Load Whisper model from custom path or cache"""
    global model
    try:
        if USE_CUSTOM_PATH and os.path.exists(CUSTOM_MODEL_PATH):
            # Load from custom path
            model = whisper.load_model(CUSTOM_MODEL_PATH)
            print(f"✅ Loaded from: {CUSTOM_MODEL_PATH}")
        else:
            # Load from cache (downloads if needed)
            model = whisper.load_model("large-v3")
            print("✅ Loaded from cache")
        return True
    except Exception as e:
        sg.popup_error(f"Failed to load Whisper model: {e}")
        return False


def browse_model_file():
    """Browse for model file"""
    filename = sg.popup_get_file('Select Whisper Model File',
                                 file_types=(("PyTorch Files", "*.pt"),))
    return filename


def create_layout():
    """Create the GUI layout"""
    layout = [
        [sg.Text('🎙️ Whisper STT Tester', font=('Arial', 16, 'bold'), justification='center')],
        [sg.HSeparator()],

        # Model path settings
        [sg.Text('Model Settings:', font=('Arial', 10, 'bold'))],
        [sg.Radio('Use Cache', 'MODEL_LOCATION', key='-USE-CACHE-', default=not USE_CUSTOM_PATH),
         sg.Radio('Use Custom Path', 'MODEL_LOCATION', key='-USE-CUSTOM-', default=USE_CUSTOM_PATH)],
        [sg.Text('Custom Path:'), sg.Input(CUSTOM_MODEL_PATH, key='-MODEL-PATH-', size=(40, 1)),
         sg.Button('Browse', key='-BROWSE-')],
        [sg.Button('Reload Model', key='-RELOAD-')],

        # Model status
        [sg.Text('Model Status:', font=('Arial', 10, 'bold')),
         sg.Text('Loading...', key='-MODEL-STATUS-', text_color='yellow')],

        [sg.HSeparator()],

        # Recording controls
        [sg.Text('Recording Controls:', font=('Arial', 12, 'bold'))],
        [sg.Button('Record 5 Seconds', key='-RECORD5-', size=(15, 2), disabled=True),
         sg.Button('Record 10 Seconds', key='-RECORD10-', size=(15, 2), disabled=True),
         sg.Button('Stop Recording', key='-STOP-', size=(15, 2))],

        # Progress bar
        [sg.Text('Progress:'), sg.ProgressBar(10, orientation='h', size=(40, 20), key='-PROGRESS-')],

        # Status
        [sg.Text('Status:'), sg.Text('Ready', key='-STATUS-', size=(50, 1))],

        [sg.HSeparator()],

        # Results
        [sg.Text('Transcription Results:', font=('Arial', 12, 'bold'))],
        [sg.Text('Language:'), sg.Text('Unknown', key='-LANGUAGE-', text_color='cyan')],
        [sg.Text('Transcribed Text:')],
        [sg.Multiline('', key='-OUTPUT-', size=(70, 8), disabled=True,
                      background_color='black', text_color='white')],

        [sg.HSeparator()],

        # Control buttons
        [sg.Button('Clear Results', key='-CLEAR-'),
         sg.Button('Test Microphone', key='-TEST-MIC-'),
         sg.Button('Exit', key='-EXIT-', button_color=('white', 'red'))]
    ]

    return layout


def record_audio(duration, window):
    global is_recording
    is_recording = True

    try:
        window['-STATUS-'].update(f"🎤 Recording for {duration} seconds...")
        window['-RECORD5-'].update(disabled=True)
        window['-RECORD10-'].update(disabled=True)
        window['-PROGRESS-'].update_bar(0, duration)

        # Record with sounddevice
        audio_data = sd.rec(int(duration * RATE), samplerate=RATE, channels=1, dtype='float32')

        # Progress bar simulation
        for i in range(duration * 10):
            if not is_recording:
                break
            time.sleep(0.1)
            window['-PROGRESS-'].update_bar(i / 10, duration)

        sd.wait()  # Wait for recording to complete

        if is_recording:
            window['-STATUS-'].update("📄 Transcribing...")
            result = model.transcribe(audio_data.flatten())

            window['-OUTPUT-'].update(result['text'])
            window['-LANGUAGE-'].update(f"Language: {result['language']}")
            window['-STATUS-'].update("✅ Transcription complete!")

    except Exception as e:
        window['-STATUS-'].update(f"❌ Error: {e}")
    finally:
        is_recording = False
        window['-RECORD5-'].update(disabled=False)
        window['-RECORD10-'].update(disabled=False)

def test_microphone():
    try:
        devices = sd.query_devices()
        input_devices = [f"Device {i}: {dev['name']}" for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]

        if input_devices:
            sg.popup_scrolled('\n'.join(input_devices), title="Available Input Devices", size=(60, 15))
        else:
            sg.popup_error("No input devices found!")
    except Exception as e:
        sg.popup_error(f"Microphone test failed: {e}")


def main():
    """Main GUI loop"""
    global model, is_recording, audio_thread, USE_CUSTOM_PATH, CUSTOM_MODEL_PATH

    layout = create_layout()
    window = sg.Window('Whisper STT Tester', layout, finalize=True, resizable=True)

    # Load model
    window['-STATUS-'].update("Loading Whisper model...")
    if load_whisper_model():
        window['-MODEL-STATUS-'].update("✅ Loaded", text_color='green')
        window['-RECORD5-'].update(disabled=False)
        window['-RECORD10-'].update(disabled=False)
        window['-STATUS-'].update("Ready to record!")
    else:
        window['-MODEL-STATUS-'].update("❌ Failed", text_color='red')
        window['-STATUS-'].update("Model loading failed!")

    while True:
        event, values = window.read(timeout=100)

        if event in (sg.WIN_CLOSED, '-EXIT-'):
            break

        elif event == '-BROWSE-':
            filename = browse_model_file()
            if filename:
                window['-MODEL-PATH-'].update(filename)

        elif event == '-RELOAD-':
            USE_CUSTOM_PATH = values['-USE-CUSTOM-']
            CUSTOM_MODEL_PATH = values['-MODEL-PATH-']

            window['-MODEL-STATUS-'].update("Loading...", text_color='yellow')
            window['-STATUS-'].update("Reloading model...")

            if load_whisper_model():
                window['-MODEL-STATUS-'].update("✅ Loaded", text_color='green')
                window['-RECORD5-'].update(disabled=False)
                window['-RECORD10-'].update(disabled=False)
                window['-STATUS-'].update("Model reloaded successfully!")
            else:
                window['-MODEL-STATUS-'].update("❌ Failed", text_color='red')
                window['-STATUS-'].update("Model reload failed!")

        elif event == '-RECORD5-' and model and not is_recording:
            audio_thread = threading.Thread(target=record_audio, args=(5, window))
            audio_thread.daemon = True
            audio_thread.start()

        elif event == '-RECORD10-' and model and not is_recording:
            audio_thread = threading.Thread(target=record_audio, args=(10, window))
            audio_thread.daemon = True
            audio_thread.start()

        elif event == '-STOP-':
            is_recording = False
            window['-STATUS-'].update("Stopping recording...")

        elif event == '-CLEAR-':
            window['-OUTPUT-'].update('')
            window['-LANGUAGE-'].update('Unknown')
            window['-STATUS-'].update('Ready')
            window['-PROGRESS-'].update_bar(0, 10)

        elif event == '-TEST-MIC-':
            test_microphone()

    is_recording = False
    window.close()


if __name__ == "__main__":
    main()

"""
pip install openai-whisper pyaudio

pip install https://download.lfd.uci.edu/pythonlibs/archived/PyAudio-0.2.11-cp311-cp311-win_amd64.whl
"""