import PySimpleGUI as sg
import asyncio
import os
from datetime import timedelta
import json
from cryptography.fernet import Fernet, InvalidToken
import re
import os
import base64
import mimetypes
from openai import OpenAI
import anthropic
import requests
from groq import Groq
from together import Together
import time
# import pyautogui  # Commented out - Not used in main project integration (kept for future agent types)
import threading
import datetime
import sys
# import mss  # Commented out - Used with PyAutoGUI (kept for future agent types)
from PIL import Image, ImageGrab, ImageFont, ImageDraw
from datetime import datetime

#Global variables
global_running = True
processing_running = False
global_responses = ["", "", "", "", ""]
stop_event = threading.Event()
TASK_COMPLETION_CONFIRMATIONS = 3
use_full_screenshot = True
FULL_SCREEN_DOT_SIZE = 20
FULL_SCREEN_FONT_SIZE = 80
CURSOR_AREA_DOT_SIZE = 10
CURSOR_AREA_FONT_SIZE = 40
SCREENSHOT_ZOOM_FACTOR = 2.0

###Handle the directory across different OS
CHAT_MODEL_LIST_FOLDER = os.path.join(os.getcwd(), "ChatModelList")
os.makedirs(CHAT_MODEL_LIST_FOLDER, exist_ok=True)

##Create logs directory
os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)
# Use a fixed encryption key
key = b'8jtTR9QcD-dXGDpLLBD8-0jqNjZBfzPHtQcnbYVYfM8='
cipher_suite = Fernet(key)

# All data used about agents is available in this class
class AgentSystem:
    def __init__(self):
        self.agent_folder = "AgentListTab/AgentList"
        self.config_folder = "AgentListTab/AgentConfig"
        os.makedirs(self.agent_folder, exist_ok=True)
        os.makedirs(self.config_folder, exist_ok=True)
        self.running_agents = set()
        self.active_agent = ""
        self.next_agent = ""
        self.last_agent = ""
        self.agent_counter = 1

    ###Create the agent as a empty text file
    def create_agent(self, agent_text, interval=None):
        next_agent_number = 1 if not os.listdir(self.agent_folder) else max(
            [int(name.split()[1].split('.')[0]) for name in os.listdir(self.agent_folder) if name.endswith('.txt')]) + 1
        agent_name = f"Agent {next_agent_number}"
        open(f"{self.agent_folder}/{agent_name}.txt", "w").close()
        return agent_name

    def delete_agent(self, agent_name):
        try:
            file_path = f"{self.agent_folder}/{agent_name}.txt"
            config_path = f"{self.config_folder}/{agent_name}_config.json"

            # Delete agent file
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete config file if exists
            if os.path.exists(config_path):
                os.remove(config_path)

            return True
        except Exception as e:
            print(f"Error deleting agent: {e}")
            return False

    def load_agents(self):
        agents = []
        if os.path.exists(self.agent_folder):
            for file in os.listdir(self.agent_folder):
                if file.endswith(".txt"):
                    agents.append(file[:-4])
        return sorted(agents)

    def load_agent_content(self, agent_name):
        file_path = f"{self.agent_folder}/{agent_name}.txt"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        return ""

    def save_agent_config(self, agent_name, schedule_type, start_date, start_time, hours=0, mins=0, secs=0,
                          provider=None, model_name=None):
        config_path = f"{self.config_folder}/{agent_name}_config.json"
        config = {
            "schedule_type": schedule_type,
            "start_date": start_date,
            "start_time": start_time,
            "hours": hours,
            "minutes": mins,
            "seconds": secs,
            "provider": provider,
            "model_name": model_name
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

    def load_agent_config(self, agent_name):
        config_path = f"{self.config_folder}/{agent_name}_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.loads(f.read())
        return None


###########################################################################
# AGENTLIST SCHEDULER - ASYNC SCHEDULING FOR AUTOMATED AGENT TRIGGERING
###########################################################################

class AgentScheduler:
    """
    Async scheduler for AgentList - handles automated agent triggering.

    Architecture:
    - Dedicated asyncio event loop in separate daemon thread
    - Async tasks for one-time and repeating agents
    - Thread-safe communication with main GUI via write_event_value()
    - Shared state dicts for display and control
    """

    def __init__(self, window, scheduled_agents, agent_stop_flags, agent_system):
        """
        Initialize scheduler with references from main app.

        Args:
            window: PySimpleGUI window reference for event triggering
            scheduled_agents: Dict shared with main app for display
            agent_stop_flags: Dict for manual stop control
            agent_system: AgentSystem instance for config/file operations
        """
        self.window = window
        self.scheduled_agents = scheduled_agents
        self.agent_stop_flags = agent_stop_flags
        self.agent_system = agent_system
        self.scheduler_loop = None
        self.running_tasks = []
        # Use print for logging since logger may not be configured in module
        self.log_prefix = "[AGENTLIST_SCHEDULER]"

    def start_scheduler_thread(self):
        """
        Start dedicated asyncio event loop in background thread.
        Call this ONCE after window creation.

        Creates event loop in main thread to avoid race conditions,
        then passes it to daemon thread for execution.
        """
        # Create event loop in main thread (avoids NoneType error)
        self.scheduler_loop = asyncio.new_event_loop()

        def run_loop():
            """Thread target: Set loop and run forever"""
            asyncio.set_event_loop(self.scheduler_loop)
            print(f"{self.log_prefix} Scheduler event loop started")
            self.scheduler_loop.run_forever()

        # Start daemon thread (auto-terminates with app)
        scheduler_thread = threading.Thread(target=run_loop, daemon=True)
        scheduler_thread.start()
        time.sleep(0.5)  # Let loop initialize
        print(f"{self.log_prefix} Scheduler thread started")

    async def schedule_one_time_agent(self, agent_name, start_datetime, task_content):
        """
        Schedule one-time agent execution (runs on scheduler_loop).

        Flow:
        1. Async sleep until scheduled time
        2. Check stop flag (allows manual cancellation)
        3. Select agent in GUI listbox
        4. Trigger -AGENT_TRIGGERED- event (thread-safe)
        5. Remove from scheduled_agents
        6. Update display

        Args:
            agent_name: Agent name (e.g., "Agent 1")
            start_datetime: datetime object for execution time
            task_content: Agent task text to execute
        """
        try:
            print(
                f"{self.log_prefix} One-time agent scheduled: {agent_name} "
                f"at {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Wait until scheduled time (non-blocking)
            delay = (start_datetime - datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

            # Check if agent was manually stopped
            if agent_name in self.agent_stop_flags and self.agent_stop_flags[agent_name]:
                print(f"{self.log_prefix} {agent_name} stopped before execution")
                return

            # ROBUST SELECTION: Select agent multiple times to ensure it's properly selected
            try:
                agent_list = self.agent_system.load_agents()
                if agent_name in agent_list:
                    agent_index = agent_list.index(agent_name)

                    # Select agent 3 times with delays to ensure GUI processes it
                    for attempt in range(3):
                        self.window['AGENT_LIST'].update(set_to_index=agent_index)
                        print(f"{self.log_prefix} Selection attempt {attempt + 1}/3: {agent_name}")
                        await asyncio.sleep(0.2)

                        # Fire AGENT_LIST event to load content (same as clicking on agent)
                        self.window.write_event_value('AGENT_LIST', None)
                        print(f"{self.log_prefix} Fired AGENT_LIST event (attempt {attempt + 1})")
                        await asyncio.sleep(0.3)

                    print(f"{self.log_prefix} Agent selection complete: {agent_name}")
            except Exception as e:
                print(f"{self.log_prefix} Error selecting agent: {e}")

            # Additional delay to ensure content is fully loaded
            await asyncio.sleep(0.5)

            # Now trigger agent execution (exactly what "Start Agent" button does)
            print(f"{self.log_prefix} ✅ Triggering one-time agent execution: {agent_name}")
            self.window.write_event_value('-AGENT_TRIGGERED-', {
                'agent_name': agent_name,
                'task': task_content,
                'execution_type': 'scheduled'
            })

            print(f"{self.log_prefix} -AGENT_TRIGGERED- event fired successfully")

            # Remove from scheduled_agents after trigger (one-time only)
            self.scheduled_agents.pop(agent_name, None)
            self.window.write_event_value('-UPDATE_SCHEDULED_DISPLAY-', True)

        except Exception as e:
            print(f"{self.log_prefix} Error in one-time agent {agent_name}: {e}")
            import traceback
            traceback.print_exc()

    async def schedule_repeat_agent(self, agent_name, start_datetime, interval, task_content):
        """
        Schedule repeating agent execution (runs on scheduler_loop).

        Flow:
        1. Async sleep until first scheduled time
        2. Loop: Select agent → Trigger → Update next_run → Sleep interval
        3. Check stop flag each iteration (allows manual stop)
        4. Remove from scheduled_agents when stopped

        Args:
            agent_name: Agent name
            start_datetime: datetime for first execution
            interval: Repeat interval in seconds
            task_content: Agent task text
        """
        try:
            print(
                f"{self.log_prefix} Repeat agent scheduled: {agent_name}, "
                f"interval: {interval}s"
            )

            # Wait until first scheduled time
            delay = (start_datetime - datetime.now()).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

            # Repeat loop (runs until manually stopped)
            while not (agent_name in self.agent_stop_flags and self.agent_stop_flags[agent_name]):
                # ROBUST SELECTION: Select agent multiple times to ensure it's properly selected
                try:
                    agent_list = self.agent_system.load_agents()
                    if agent_name in agent_list:
                        agent_index = agent_list.index(agent_name)

                        # Select agent 3 times with delays to ensure GUI processes it
                        for attempt in range(3):
                            self.window['AGENT_LIST'].update(set_to_index=agent_index)
                            print(f"{self.log_prefix} Selection attempt {attempt + 1}/3: {agent_name}")
                            await asyncio.sleep(0.2)

                            # Fire AGENT_LIST event to load content (same as clicking on agent)
                            self.window.write_event_value('AGENT_LIST', None)
                            print(f"{self.log_prefix} Fired AGENT_LIST event (attempt {attempt + 1})")
                            await asyncio.sleep(0.3)

                        print(f"{self.log_prefix} Agent selection complete: {agent_name}")
                except Exception as e:
                    print(f"{self.log_prefix} Error selecting agent: {e}")

                # Additional delay to ensure content is fully loaded
                await asyncio.sleep(0.5)

                # Trigger agent execution via GUI event
                print(f"{self.log_prefix} ✅ Triggering repeat agent: {agent_name}")
                self.window.write_event_value('-AGENT_TRIGGERED-', {
                    'agent_name': agent_name,
                    'task': task_content,
                    'execution_type': 'scheduled'
                })

                # Update next run time
                next_run = datetime.now() + timedelta(seconds=interval)
                self.scheduled_agents[agent_name]['next_run'] = next_run
                self.window.write_event_value('-UPDATE_SCHEDULED_DISPLAY-', True)
                print(
                    f"{self.log_prefix} Next run for {agent_name}: "
                    f"{next_run.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # Wait for interval (non-blocking)
                await asyncio.sleep(interval)

            # Stopped manually
            print(f"{self.log_prefix} Repeat agent stopped: {agent_name}")
            self.scheduled_agents.pop(agent_name, None)
            self.window.write_event_value('-UPDATE_SCHEDULED_DISPLAY-', True)

        except Exception as e:
            print(f"{self.log_prefix} Error in repeat agent {agent_name}: {e}")
            import traceback
            traceback.print_exc()

    def appoint_agent(self, agent_name, schedule_type, start_datetime, interval, task_content):
        """
        Main entry point: Appoint agent for scheduling.

        Called from main event loop (synchronous context).
        Submits async task to scheduler_loop via run_coroutine_threadsafe().

        Args:
            agent_name: Agent name
            schedule_type: "one-time" or "repeat"
            start_datetime: datetime object for first run
            interval: Interval in seconds (0 for one-time)
            task_content: Agent task text

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate datetime is in future
            if start_datetime <= datetime.now():
                print(f"{self.log_prefix} Error: Start datetime must be in future")
                return False

            # Initialize stop flag
            self.agent_stop_flags[agent_name] = False

            if schedule_type == "one-time":
                # Add to dict for display
                self.scheduled_agents[agent_name] = {
                    'next_run': start_datetime,
                    'interval': 0,
                    'type': 'one-time',
                    'task': task_content
                }

                # Create async task on scheduler event loop (thread-safe)
                task = asyncio.run_coroutine_threadsafe(
                    self.schedule_one_time_agent(agent_name, start_datetime, task_content),
                    self.scheduler_loop
                )
                self.running_tasks.append(task)
                print(f"{self.log_prefix} One-time agent appointed: {agent_name}")

            else:  # repeat
                # Add to dict for display
                self.scheduled_agents[agent_name] = {
                    'next_run': start_datetime,
                    'interval': interval,
                    'type': 'repeat',
                    'task': task_content
                }

                # Create async task on scheduler event loop (thread-safe)
                task = asyncio.run_coroutine_threadsafe(
                    self.schedule_repeat_agent(agent_name, start_datetime, interval, task_content),
                    self.scheduler_loop
                )
                self.running_tasks.append(task)
                print(
                    f"{self.log_prefix} Repeat agent appointed: {agent_name}, "
                    f"interval: {interval}s"
                )

            # Update display
            self.window.write_event_value('-UPDATE_SCHEDULED_DISPLAY-', True)
            return True

        except Exception as e:
            print(f"{self.log_prefix} Error appointing agent: {e}")
            import traceback
            traceback.print_exc()
            return False

    def stop_agent(self, agent_name):
        """
        Stop a scheduled or running agent.

        Sets stop flag to cancel async task.
        Removes from scheduled_agents dict.
        Updates display.

        Args:
            agent_name: Agent name to stop
        """
        self.agent_stop_flags[agent_name] = True
        self.scheduled_agents.pop(agent_name, None)
        self.window.write_event_value('-UPDATE_SCHEDULED_DISPLAY-', True)
        print(f"{self.log_prefix} Agent stopped: {agent_name}")


def format_scheduled_agents_display(scheduled_agents):
    """
    Helper function to format scheduled agents for display.

    Args:
        scheduled_agents: Dict of scheduled agents

    Returns:
        str: Formatted string for GUI display
    """
    if not scheduled_agents:
        return "None"

    sorted_agents = sorted(scheduled_agents.items(), key=lambda x: x[1]['next_run'])
    formatted = []

    for agent_name, data in sorted_agents:
        next_run = data['next_run'].strftime('%Y-%m-%d %H:%M:%S')
        schedule_type = data.get('type', 'unknown')

        if schedule_type == 'repeat':
            interval = data.get('interval', 0)
            hours = interval // 3600
            mins = (interval % 3600) // 60
            secs = interval % 60
            formatted.append(
                f"{agent_name} (Next: {next_run}, "
                f"Repeat: {hours}h {mins}m {secs}s)"
            )
        else:
            formatted.append(f"{agent_name} (Next: {next_run}, One-time)")

    return "\n".join(formatted)


###Extra function codes#####
def minimize_active_window(window_title):
    try:
        if sys.platform == "win32":
            import win32gui
            def enum_windows_callback(hwnd, result):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) == window_title:
                    result.append(hwnd)
                return True

            result = []
            win32gui.EnumWindows(enum_windows_callback, result)
            if result:
                win32gui.ShowWindow(result[0], 6)  # 6 is the constant for SW_MINIMIZE
            else:
                print(f"Window with title '{window_title}' not found")
        elif sys.platform == "darwin":  # macOS
            import subprocess

            apple_script = f'''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                if frontApp is "{window_title}" then
                    keystroke "m" using command down
                end if
            end tell
            '''
            subprocess.run(["osascript", "-e", apple_script])
        elif sys.platform.startswith("linux"):
            import subprocess
            subprocess.run(["wmctrl", "-ir", "$(xdotool getactivewindow)", "-b", "add,hidden"])
        else:
            print("Unsupported operating system for minimizing active window")

        time.sleep(0.5)  # Short pause after minimizing
    except Exception as e:
        print(f"Error minimizing active window: {str(e)}")

# ========== PyAutoGUI SCREENSHOT FUNCTIONS COMMENTED OUT (NOT USED IN MAIN PROJECT) ==========
# Kept for future agent types that may need screenshot functionality
#
# def capture_and_update_screenshots():
#     global use_full_screenshot
#
#     # Ensure screenshot directory exists
#     screenshots_dir = os.path.join(os.getcwd(), "screenshots")
#     os.makedirs(screenshots_dir, exist_ok=True)
#
#     # Get current mouse position
#     cursor_pos = pyautogui.position()
#
#     if use_full_screenshot:
#         # Capture full screen
#         screenshot_path = capture_full_screen()
#         screenshot_type = "full_screen"
#     else:
#         # Capture cursor area
#         screenshot_path = capture_cursor_area()
#         screenshot_type = "cursor_area"
#
#     # Toggle for next capture
#     use_full_screenshot = not use_full_screenshot
#
#     return screenshot_path, screenshot_type, cursor_pos
#
#
# def capture_full_screen():
#     screenshots_dir = os.path.join(os.getcwd(), "screenshots")
#     output_path = os.path.join(screenshots_dir, "latest_full_screen.jpg")
#
#     with mss.mss() as sct:
#         monitor = sct.monitors[1]
#         screen_width = monitor["width"]
#         screen_height = monitor["height"]
#
#         region = {"top": 0, "left": 0, "width": screen_width, "height": screen_height}
#         screenshot = sct.grab(region)
#         img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
#
#         zoomed_width = int(screen_width * SCREENSHOT_ZOOM_FACTOR )
#         zoomed_height = int(screen_height * SCREENSHOT_ZOOM_FACTOR )
#         zoomed_img = img.resize((zoomed_width, zoomed_height), Image.Resampling.LANCZOS)
#
#         mouse_x, mouse_y = pyautogui.position()
#         draw = ImageDraw.Draw(zoomed_img)
#
#         zoomed_mouse_x = int(mouse_x * 2.0)
#         zoomed_mouse_y = int(mouse_y * 2.0)
#
#         draw.ellipse([zoomed_mouse_x - FULL_SCREEN_DOT_SIZE, zoomed_mouse_y - FULL_SCREEN_DOT_SIZE,
#                       zoomed_mouse_x + FULL_SCREEN_DOT_SIZE, zoomed_mouse_y + FULL_SCREEN_DOT_SIZE],
#                      fill='red')
#
#         coord_text = f"({mouse_x}, {mouse_y})"
#         for offset_x, offset_y in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
#             draw.text((zoomed_mouse_x + offset_x - FULL_SCREEN_DOT_SIZE,
#                        zoomed_mouse_y + offset_y + FULL_SCREEN_DOT_SIZE + 5),
#                       coord_text, fill='black', font_size=FULL_SCREEN_FONT_SIZE)
#         draw.text((zoomed_mouse_x - FULL_SCREEN_DOT_SIZE, zoomed_mouse_y + FULL_SCREEN_DOT_SIZE + 5),
#                   coord_text, fill='orange', font_size=FULL_SCREEN_FONT_SIZE)
#
#         return compress_image(zoomed_img, 3, 'JPEG', output_path)
#
#
# def capture_cursor_area():
#     screenshots_dir = os.path.join(os.getcwd(), "screenshots")
#     output_path = os.path.join(screenshots_dir, "latest_cursor_area.png")
#
#     with mss.mss() as sct:
#         monitor = sct.monitors[1]
#         screen_width = monitor["width"]
#         screen_height = monitor["height"]
#         mouse_x, mouse_y = pyautogui.position()
#
#         capture_width = screen_width // SCREENSHOT_ZOOM_FACTOR
#         capture_height = screen_height // SCREENSHOT_ZOOM_FACTOR
#
#         x1 = max(0, mouse_x - capture_width // 2)
#         y1 = max(0, mouse_y - capture_height // 2)
#         x2 = min(screen_width, x1 + capture_width)
#         y2 = min(screen_height, y1 + capture_height)
#
#         if x2 >= screen_width:
#             x1 = screen_width - capture_width
#         if y2 >= screen_height:
#             y1 = screen_height - capture_height
#
#         region = {"top": int(y1), "left": int(x1),
#                   "width": int(capture_width), "height": int(capture_height)}
#
#         screenshot = sct.grab(region)
#         img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
#         zoomed_img = img.resize((screen_width, screen_height), Image.Resampling.LANCZOS)
#
#         draw = ImageDraw.Draw(zoomed_img)
#         rel_x = (mouse_x - x1) * 2.0
#         rel_y = (mouse_y - y1) * 2.0
#
#         draw.ellipse([rel_x - CURSOR_AREA_DOT_SIZE, rel_y - CURSOR_AREA_DOT_SIZE,
#                       rel_x + CURSOR_AREA_DOT_SIZE, rel_y + CURSOR_AREA_DOT_SIZE],
#                      fill='red')
#
#         coord_text = f"({mouse_x}, {mouse_y})"
#         for offset_x, offset_y in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
#             draw.text((rel_x + offset_x - CURSOR_AREA_DOT_SIZE,
#                        rel_y + offset_y + CURSOR_AREA_DOT_SIZE + 5),
#                       coord_text, fill='black', font_size=CURSOR_AREA_FONT_SIZE)
#         draw.text((rel_x - CURSOR_AREA_DOT_SIZE, rel_y + CURSOR_AREA_DOT_SIZE + 5),
#                   coord_text, fill='orange', font_size=CURSOR_AREA_FONT_SIZE)
#
#         return compress_image(zoomed_img, 3, 'PNG', output_path)

def compress_image(img, max_size_mb, file_type, output_path):
    from io import BytesIO

    max_size_bytes = max_size_mb * 1024 * 1024
    temp_buffer = BytesIO()

    # Initial save at high quality
    quality = 95
    if file_type == 'PNG':
        img.save(temp_buffer, format='PNG')
    else:
        img.convert('RGB').save(temp_buffer, format='JPEG', quality=quality, optimize=True)

    original_size = temp_buffer.tell()
    if original_size <= max_size_bytes:
        img.save(output_path, format=file_type)
        return output_path

    # Compression needed
    if file_type == 'PNG':
        # Try lossless compression
        img.save(output_path, format='PNG', optimize=True, compression_level=9)
        if os.path.getsize(output_path) <= max_size_bytes:
            return output_path

        # Try color reduction
        img = img.quantize(colors=256, method=2).convert('RGB')
        img.save(output_path, format='PNG', optimize=True, compression_level=9)
        return output_path

    else:  # JPEG compression
        while quality > 30:
            temp_buffer = BytesIO()
            img.save(temp_buffer, format='JPEG', quality=quality, optimize=True)
            if temp_buffer.tell() <= max_size_bytes:
                img.save(output_path, format='JPEG', quality=quality, optimize=True)
                return output_path
            quality -= 5

        # Maximum compression
        img.save(output_path, format='JPEG', quality=30, optimize=True)
        return output_path

#Extra function codes End######

####### New Login Tab coding START###############
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def save_api_key(api_key, provider, model_name):
    encrypted_api_key = cipher_suite.encrypt(api_key.encode())
    save_data(encrypted_api_key.decode(), f"{provider}_{model_name}_api_key")
    save_data(model_name, f"{provider}_{model_name}_model_name")
    save_last_used_model(provider, model_name)  # Add this line
    print(f"Saved API key and model name for {provider}_{model_name}")

def save_data(data, file_name):
    sanitized_file_name = sanitize_filename(file_name)
    full_path = os.path.join(CHAT_MODEL_LIST_FOLDER, f"{sanitized_file_name}.txt")
    with open(full_path, "w") as file:
        file.write(data)
    print(f"Saved data to {full_path}")

def load_data(file_name):
    try:
        sanitized_file_name = sanitize_filename(file_name)
        with open(os.path.join(CHAT_MODEL_LIST_FOLDER, f"{sanitized_file_name}.txt"), "r") as file:
            data = file.read()
        return data
    except FileNotFoundError:
        print(f"File not found: {sanitized_file_name}.txt")
        return ""
    except Exception as e:
        print(f"Error loading {sanitized_file_name}.txt: {str(e)}")
        return ""

def get_saved_models():
    saved_models = []
    print(f"Checking for saved models in: {CHAT_MODEL_LIST_FOLDER}")
    for filename in os.listdir(CHAT_MODEL_LIST_FOLDER):
        if filename.endswith("_model_name.txt"):
            sanitized_name = filename.rsplit('_model_name.txt', 1)[0]
            provider, model_name = sanitized_name.split('_', 1)
            # Restore any underscores in the model name that were from sanitization
            model_name = model_name.replace('_', '/')
            saved_model = f"{provider} - {model_name}"
            saved_models.append(saved_model)
            print(f"Found saved model: {saved_model}")
    return saved_models

def load_api_key(provider, model_name):
    try:
        encrypted_api_key = load_data(f"{provider}_{model_name}_api_key")
        if encrypted_api_key:
            decrypted_api_key = cipher_suite.decrypt(encrypted_api_key.encode()).decode()
            return decrypted_api_key
        else:
            print(f"No encrypted API key found for {provider}_{model_name}")
            return ""
    except InvalidToken:
        print(f"Invalid token for {provider}_{model_name}")
        return ""
    except Exception as e:
        print(f"Error decrypting API key for {provider}_{model_name}: {str(e)}")
        return ""

def load_model_config(provider, model_name):
    api_key = load_api_key(provider, model_name)
    loaded_model_name = load_data(f"{provider}_{model_name}_model_name")
    print(f"Loaded model name: {loaded_model_name}, API key found: {'Yes' if api_key else 'No'}")
    return  loaded_model_name,api_key

def remove_model_config(provider, model_name):
    try:
        os.remove(os.path.join(CHAT_MODEL_LIST_FOLDER , f"{provider}_{model_name}_api_key.txt"))
        os.remove(os.path.join(CHAT_MODEL_LIST_FOLDER , f"{provider}_{model_name}_model_name.txt"))
        return True
    except FileNotFoundError:
        return False

def save_last_used_model(provider, model_name):
    with open("last_used_model.txt", "w") as f:
        f.write(f"{provider},{model_name}")

def load_last_used_model():
    try:
        with open("last_used_model.txt", "r") as f:
            provider, model_name = f.read().split(',')
        return provider, model_name
    except FileNotFoundError:
        return None, None
####### New Login Tab coding END###############

# Login layout function
def create_login_layout():
    input_width = 50
    providers = ["OpenAI", "Anthropic","Google", "x.ai", "Groq", "Together.ai"]  # Add more providers as needed
    saved_models = get_saved_models()

    login_layout = [
        [sg.Text("Cloud Provider:", size=(15, 1)),
         sg.Combo(providers, default_value="OpenAI", key="-PROVIDER-", size=(input_width, 1))],
        [sg.Text("AI Model Name:", size=(15, 1)),
         sg.InputText(key="-MODEL_NAME-", size=(input_width, 1))],
        [sg.Text("API Key:", size=(15, 1)),
         sg.InputText(key="-API_KEY-", password_char="*", size=(input_width, 1))],
        [sg.Button("Save", key="-SAVE-"),
         sg.Button("Load", key="-LOAD-"),
         sg.Button("Remove", key="-REMOVE-")],
        [sg.Text("Saved Models:", size=(30, 1))],
        [sg.Listbox(values=saved_models, size=(input_width, 50), key="-SAVED_MODELS-", enable_events=True)]
    ]
    return login_layout


class AgentExecutor:
    def __init__(self):
        self.response_window = None
        self.window = None
        self.active_agents = {}
        self.scheduled_agents = {}
        self.stop_flags = {}
        self.screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def set_window(self, window):
        self.window = window
        #self.response_window = window['MODEL_RESPONSE_WINDOW']

    def get_sub_task_number(self, agent_name):
        chat_file_path = os.path.join("AgentListTab/AgentList", f"{agent_name}.txt")
        with open(chat_file_path, 'r') as file:
            content = file.read()
        sub_tasks = content.split("User: ")
        return len(sub_tasks) - 1

    def initialize_screenshots(self):
        self.screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    def cleanup_screenshots(self):
        if os.path.exists(self.screenshots_dir):
            for file in os.listdir(self.screenshots_dir):
                os.unlink(os.path.join(self.screenshots_dir, file))

    def write_responses_to_file(self):
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(logs_dir, exist_ok=True)

            # Write responses
            log_file = os.path.join(logs_dir, "last_ai_responses.txt")
            with open(log_file, "w") as file:
                for i, response in enumerate(global_responses, 1):
                    file.write(f"[RESPONSE {i} START]\n{response}\n[RESPONSE {i} END]\n\n")

            # Write screenshot info
            screenshot_log = os.path.join(logs_dir, "screenshot_log.txt")
            with open(screenshot_log, "a") as file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file.write(f"\n[{timestamp}] Screenshots captured and used in latest response\n")

        except Exception as e:
            # Update error display if writing fails
            if hasattr(self, 'window'):
                self.window['-ERROR-'].update(f"Error writing logs: {str(e)}")

    def execute_with_model(self, provider, model_name, api_key, full_prompt, screenshot_path):
        try:
            if provider == "OpenAI":
                return self._get_openai_response(full_prompt, api_key, model_name, screenshot_path)
            elif provider == "Anthropic":
                return self._get_anthropic_response(full_prompt, api_key, model_name, screenshot_path)
            elif provider == "Google":
                return self._get_google_response(full_prompt, screenshot_path, api_key, model_name)
            elif provider == "x.ai":
                return self._get_xai_response(full_prompt, screenshot_path, api_key, model_name)
            elif provider == "Groq":
                return self._get_groq_response(full_prompt, screenshot_path, api_key, model_name)
            elif provider == "Together.ai":
                return self._get_together_response(full_prompt, screenshot_path, api_key, model_name)
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            return f"Error in {provider} API call: {str(e)}"

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _get_openai_response(self, prompt, api_key, model_name, image_path):
        client = OpenAI(api_key=api_key)
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
            ]}
        ]
        response = client.chat.completions.create(model=model_name, messages=messages)
        return response.choices[0].message.content

    def _get_anthropic_response(self, prompt, api_key, model_name, image_path):
        client = anthropic.Anthropic(api_key=api_key)
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64_image
                }
            },
            {"type": "text", "text": prompt}
        ]

        message = client.messages.create(
            model=model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}]
        )
        return message.content[0].text

    def _get_google_response(self, prompt, image_path, api_key, model_name):
        client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        response = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]
            }]
        )
        return response.choices[0].message.content

    def _get_xai_response(self, prompt, image_path, api_key, model_name):
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                        "detail": "high"
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.01,
            stream=False
        )
        return response.choices[0].message.content

    def _get_groq_response(self, prompt, image_path, api_key, model_name):
        client = Groq(api_key=api_key)
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        response = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]
            }],
            model=model_name
        )
        return response.choices[0].message.content

    def _get_together_response(self, prompt, image_path, api_key, model_name):
        os.environ['TOGETHER_API_KEY'] = api_key
        client = Together()
        base64_image = self._encode_image(image_path)
        mime_type = "image/png" if image_path.lower().endswith('.png') else "image/jpeg"

        response = client.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]
            }],
            max_tokens=512,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"]
        )
        return response.choices[0].message.content

    # Process the response of the AI model for execution of the task
    def process_response(self, response_text):
        global global_responses

        # Debug logging
        print("\n=== AI MODEL RESPONSE ===")
        print(response_text)
        print("\n=== EXTRACTED COMMANDS ===")

        commands = self._extract_commands(response_text)
        print(f"Commands to execute: {commands}")

        action_start = response_text.find("###ACTION START###")
        action_end = response_text.find("###ACTION END###")
        if action_start != -1 and action_end != -1:
            action_content = response_text[action_start + len("###ACTION START###"):action_end].strip()
            task_completed = action_content.strip() == "TASK_COMPLETED"
        else:
            task_completed = False

        execution_results = []
        if not task_completed and commands:
            for command in commands:
                try:
                    print(f"\nExecuting: {command}")
                    eval(command)
                    execution_results.append(f"Executed: {command}")
                    print(f"Success: {command}")
                except Exception as e:
                    error_msg = f"Error: {command} - {str(e)}"
                    print(error_msg)
                    execution_results.append(error_msg)

        global_responses.pop(0)
        global_responses.append(response_text)
        self.write_responses_to_file()

        return execution_results, task_completed

    # ========== PyAutoGUI METHOD COMMENTED OUT (NOT USED IN MAIN PROJECT) ==========
    # def _extract_commands(self, response_text):
    #     try:
    #         pyautogui.MINIMUM_DURATION = 0.5
    #         pyautogui.PAUSE = 0.5
    #
    #         action_start = response_text.find("###ACTION START###")
    #         action_end = response_text.find("###ACTION END###")
    #         if action_start == -1 or action_end == -1:
    #             return []
    #
    #         action_content = response_text[action_start + len("###ACTION START###"):action_end].strip()
    #
    #         if action_content == "TASK_COMPLETED":
    #             return ["TASK_COMPLETED"]
    #
    #         # Comprehensive list of valid keys for keyboard operations
    #         valid_keys = [
    #             # Navigation keys
    #             'enter', 'return', 'tab', 'space', 'backspace', 'delete', 'esc', 'escape',
    #             'up', 'down', 'left', 'right', 'home', 'end', 'pageup', 'pagedown', 'insert',
    #
    #             # Function keys
    #             'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
    #
    #             # Modifier keys
    #             'ctrl', 'alt', 'shift', 'win', 'command', 'cmd', 'option', 'altright', 'shiftright', 'ctrlright',
    #
    #             # Lock keys
    #             'capslock', 'numlock', 'scrolllock',
    #
    #             # Numpad
    #             'num0', 'num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'num7', 'num8', 'num9',
    #             'numenter', 'decimal', 'add', 'subtract', 'multiply', 'divide',
    #
    #             # Media/Volume keys
    #             'volumemute', 'volumedown', 'volumeup', 'playpause', 'browserback', 'browserforward',
    #
    #             # Common combinations
    #             'ctrl+c', 'ctrl+v', 'ctrl+x', 'ctrl+z', 'ctrl+a', 'ctrl+s'
    #         ]
    #
    #         valid_methods = {
    #             # Mouse operations
    #             'moveRel': True,
    #             'click': True,
    #             'doubleClick': True,
    #             'rightClick': True,
    #             'mouseDown': True,
    #             'mouseUp': True,
    #             'dragRel': True,
    #             'dragTo': True,
    #             'scroll': True,
    #
    #             # Keyboard operations
    #             'write': True,
    #             'press': lambda args: any(key in str(args).lower() for key in valid_keys),
    #             'hotkey': lambda args: all(key in valid_keys for key in str(args).lower().split(',')),
    #             'typewrite': True,
    #             'keyDown': lambda args: any(key in str(args).lower() for key in valid_keys),
    #             'keyUp': lambda args: any(key in str(args).lower() for key in valid_keys)
    #         }
    #
    #         pattern = r'pyautogui\.(\w+)\(([^)]*)\)'
    #         matches = re.finditer(pattern, action_content)
    #
    #         valid_commands = []
    #         for match in matches:
    #             method, args = match.groups()
    #             if method in valid_methods:
    #                 if callable(valid_methods[method]):
    #                     if valid_methods[method](args):
    #                         valid_commands.append(f"pyautogui.{method}({args})")
    #                 else:
    #                     valid_commands.append(f"pyautogui.{method}({args})")
    #
    #         return valid_commands
    #
    #     except Exception as e:
    #         if self.window:
    #             self.window.write_event_value('-ERROR-', f"Error extracting commands: {str(e)}")
    #         return []

    def format_scheduled_agents(self):
        if not self.scheduled_agents:
            return "None"

        sorted_agents = sorted(self.scheduled_agents.items(), key=lambda x: x[1]['next_run'])
        formatted = []
        for agent, data in sorted_agents:
            next_run = data['next_run'].strftime('%Y-%m-%d %H:%M:%S')
            formatted.append(f"{agent} (Next: {next_run})")
        return "\n".join(formatted)

    def cleanup_agent(self, agent_name):
        self.active_agents.pop(agent_name, None)
        self.stop_flags.pop(agent_name, None)

    ###Type of execution whether one time or repetition
    def handle_execution(self, agent_name, is_onetime, start_datetime=None):
        if is_onetime:
            self.scheduled_agents[agent_name] = {'next_run': start_datetime, 'interval': 0}
        else:
            self.active_agents[agent_name] = True

    def manage_screenshots(self, agent_name):
        self.cleanup_screenshots()
        self.initialize_screenshots()

    # ========== PyAutoGUI METHOD COMMENTED OUT (NOT USED IN MAIN PROJECT) ==========
    # def get_automated_pre_prompt(self):
    #     return """This is a computer automation task using PyAutoGUI library. You'll receive ONE screenshot per prompt, alternating between:
    # - Full screen (200% zoom, JPEG)
    # - Cursor area (200% zoom, PNG)
    # Each shows cursor position with red dot and X,Y coordinates.
    #
    # Required format for each response:
    #
    # ###SUMMARY START###
    # - Task StartTime: When task started in format [YYYY-MM-DD HH:MM:SS]. Must remain fixed until Task completion.
    # - Current Timestamp: [Current YYYY-MM-DD HH:MM:SS]
    # - Current Cursor(red dot) position: [Current X,Y coordinates]
    # - Previous cursor position: [Last X,Y from previous response]
    # - Time elapsed since last action and from Task StartTime
    # - Movement or mouse click verification (success/failure) if required
    # - Actions attempted and their outcomes based on latest screenshot state and all previous 5 responses including the last 5 summaries
    # ###SUMMARY END###
    #
    # ###PLANNING START###
    # Plan 1: Primary approach based on cursor position and current state of screen
    # Plan 2: Alternative if Plan 1 fails or no movement detected
    # Each plan should target one specific action
    # ###PLANNING END###
    #
    # ###ACTION START###
    # Execute ONLY ONE of these per response:
    #
    # 1. Mouse Movement:
    # - pyautogui.moveRel(x, y) - Use ONLY relative movements
    # - NO coordinate-based clicks
    # - Always verify cursor position visually before clicking
    #
    # 2. Mouse Clicks (Only after visual position verification):
    # - pyautogui.click() - Single click
    # - pyautogui.doubleClick() - Double click
    # - pyautogui.rightClick() - Right click
    # - pyautogui.mouseDown() - Press mouse button
    # - pyautogui.mouseUp() - Release mouse button
    # - pyautogui.dragRel() - Drag mouse
    # - pyautogui.scroll() - Scroll wheel
    #
    # 3. Keyboard Operations:
    # Navigation Keys:
    # - enter, return, tab, space, backspace, delete
    # - esc, escape, insert
    # - up, down, left, right
    # - home, end, pageup, pagedown
    #
    # Function Keys:
    # - f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12
    #
    # Modifier Keys:
    # - ctrl, alt, shift, win, command, cmd, option
    # - altright, shiftright, ctrlright
    #
    # Lock Keys:
    # - capslock, numlock, scrolllock
    #
    # Numpad:
    # - num0-num9, numenter, decimal
    # - add, subtract, multiply, divide
    #
    # Media/Volume:
    # - volumemute, volumedown, volumeup
    # - playpause, browserback, browserforward
    #
    # Common Combinations:
    # - ctrl+c, ctrl+v, ctrl+x, ctrl+z, ctrl+a, ctrl+s
    #
    # Keyboard Commands:
    # - pyautogui.write('text') - Type text
    # - pyautogui.press('key') - Press single key
    # - pyautogui.hotkey('key1','key2') - Key combinations
    # - pyautogui.keyDown('key') - Hold key
    # - pyautogui.keyUp('key') - Release key
    #
    # Close any unnecessary windows opened once task is completed and respond with 'TASK_COMPLETED' when task is completed. Keep replying 'TASK_COMPLETED' if multiple confirmations needed to end loop.
    # ###ACTION END###"""

    # ========== PyAutoGUI METHOD COMMENTED OUT (NOT USED IN MAIN PROJECT) ==========
    # def construct_full_prompt(self, agent_name, current_prompt, pre_prompt, screenshot_path, screenshot_type,
    #                           global_responses):
    #     timestamp =datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     cursor_pos = pyautogui.position()
    #
    #     response_text = ""
    #     for i, response in enumerate(global_responses, 1):
    #         if response.strip():
    #             response_text += f"[RESPONSE {i} START]\n{response}\n[RESPONSE {i} END]\n\n"
    #
    #     return f"""<image_section>
    # SCREENSHOT:
    # Type: {screenshot_type}
    # Path: {screenshot_path}
    # </image_section>
    #
    # <text_section>
    # {pre_prompt}
    # TIMESTAMP: {timestamp}
    # CURSOR: X={cursor_pos[0]}, Y={cursor_pos[1]}
    # PREVIOUS RESPONSES:
    # {response_text}
    # FULL TASK:
    # {current_prompt}
    # </text_section>"""


# Everything related to the GUI functions
class GUI:
    def __init__(self):
        self.system = AgentSystem()
        self.scheduled_agents = {}
        self.active_agents = {}
        self.agent_timeouts = {}
        self.stop_flags = {}
        #Agent executer function call for main actions from models.
        self.agent_executor = AgentExecutor()
        #We have to wait for agents to load
        #self.load_all_agent_schedules()

        control_frames_layout = [
            [sg.Frame('Schedule Settings', [
                [sg.Radio('One-time', 'SCHEDULE_TYPE', key='-ONE_TIME-', default=True),
                 sg.Radio('Repeat', 'SCHEDULE_TYPE', key='-REPEAT-')],
                [sg.Text('Start Date:'),
                 sg.Input(key='-START_DATE-', size=(15, 1)),
                 sg.CalendarButton('Choose', target='-START_DATE-', format='%Y-%m-%d')],
                [sg.Text('Start Time:')],
                [sg.Column([
                    [sg.Combo(values=[f"{i:02d}" for i in range(24)], default_value='00', size=(3, 1),
                              key='-START_HOUR-')],
                    [sg.Text('Hour')]
                ]), sg.Text(':'),
                    sg.Column([
                        [sg.Combo(values=[f"{i:02d}" for i in range(60)], default_value='00', size=(3, 1),
                                  key='-START_MIN-')],
                        [sg.Text('Min')]
                    ]), sg.Text(':'),
                    sg.Column([
                        [sg.Combo(values=[f"{i:02d}" for i in range(60)], default_value='00', size=(3, 1),
                                  key='-START_SEC-')],
                        [sg.Text('Sec')]
                    ])],
                [sg.Text('Repeat Interval:')],
                [sg.Column([
                    [sg.Input('24', key='HOUR_COMBO', size=(3, 1))],
                    [sg.Text('Hour')]
                ]), sg.Text(':'),
                    sg.Column([
                        [sg.Input('0', key='MIN_COMBO', size=(3, 1))],
                        [sg.Text('Min')]
                    ]), sg.Text(':'),
                    sg.Column([
                        [sg.Input('0', key='SEC_COMBO', size=(3, 1))],
                        [sg.Text('Sec')]
                    ])]
            ]),
             sg.Frame('Agent Control Settings', [
                 [sg.Text('Max Attempts:'), sg.Input('1000000', key='MAX_ATTEMPTS', size=(6, 1))],
                 [sg.Text('Max Time:')],
                 [sg.Input('72', key='TIME_HOURS', size=(6, 1)), sg.Text('Hours')],
                 [sg.Input('0', key='TIME_MINS', size=(6, 1)), sg.Text('Mins')],
                 [sg.Input('0', key='TIME_SECS', size=(6, 1)), sg.Text('Secs')]
             ])]
        ]

        agent_list_layout = [
            [sg.Button('Create Agent', button_color='DarkBlue', size=(24, 2)),
             sg.Button('Delete Agent', button_color='DarkRed', size=(24, 2))],
            [sg.Button('Start Agent', button_color='green', size=(24, 2)),
             sg.Button('Stop Agent', button_color='red', size=(24, 2))],
            [sg.Listbox(values=[], size=(30, 10), key='AGENT_LIST', enable_events=True, expand_y=True, expand_x=True)],
            [sg.Button('Appoint Agent', button_color='DarkGreen', size=(17, 2)),
             sg.Button('Save Agent', button_color='DarkBlue', size=(17, 2))],
            [sg.Column(control_frames_layout)]
        ]

        chat_layout = [
            [sg.Text('Action Window', font=('Any', 12, 'bold'))],
            [sg.Multiline(size=(60, 25), key='CHAT_HISTORY', font=('Any', 11), disabled=False, expand_x=True,
                          expand_y=True)],
            [sg.Multiline(key='CHAT_INPUT', size=(95, 5), font=('Any', 11)),
             sg.Button('Send', button_color='Blue', size=(20, 4), font=('Any', 11))]
        ]

        status_layout = [
            [sg.Text('Agent Status:', font=('Any', 11, 'bold')), sg.Text('', key='AGENT_STATUS', font=('Any', 11))],
            [sg.Text('Active Agent: '), sg.Text('None', key='-ACTIVE-')],
            [sg.Text('Next Scheduled Agent: '), sg.Text('None', key='-NEXT-')],
            [sg.Text('All Scheduled Agents: '), sg.Text('None', key='-ALL-SCHEDULED-')],
            [sg.Text('Last Agent: '), sg.Text('None', key='-LAST-')],
            [sg.Text('Error: ', text_color='red'), sg.Text('None', key='-ERROR-', text_color='red')]
        ]

        login_layout = create_login_layout()

        agents_list_tab = [
            [sg.Column(agent_list_layout, expand_x=True, expand_y=True),
             sg.VSeparator(),
             sg.Column(chat_layout, expand_x=True, expand_y=True),
             sg.VSeparator(),
             sg.Column(status_layout, expand_x=True, expand_y=True)]
        ]

        tab_group_layout = [
            [sg.Tab('AgentsList', agents_list_tab, key='TAB_AGENTS_LIST'),
             sg.Tab('Login', login_layout, key='TAB_LOGIN')]
        ]

        # ========== GUI WINDOW CREATION REMOVED (NOW INTEGRATED INTO MAIN PROJECT) ==========
        # self.window = sg.Window('AGI IN ACTION 1.0',
        #                         [[sg.TabGroup(tab_group_layout, expand_x=True, expand_y=True)]],
        #                         finalize=True,
        #                         resizable=True)
        # self.window.Maximize()# Launch in full screen mode

        # Load last used model after window creation
        # provider, model_name = load_last_used_model()
        # if provider and model_name:
        #     self.window["-PROVIDER-"].update(provider)
        #     self.window["-MODEL_NAME-"].update(model_name)
        #     api_key = load_api_key(provider, model_name)
        #     if api_key:
        #         self.window["-API_KEY-"].update(api_key)

        # self.window.bind('<Return>', 'Send')
        # self.window['AGENT_LIST'].update(self.system.load_agents())
        # self.running_tasks = []
        # self.agent_executor.set_window(self.window)
        # ========== END OF REMOVED GUI WINDOW CREATION ==========
        pass  # Placeholder to keep class structure valid

    def get_interval(self, values):
        hours = int(values['HOUR_COMBO'] or 0)
        mins = int(values['MIN_COMBO'] or 0)
        secs = int(values['SEC_COMBO'] or 0)
        return hours * 3600 + mins * 60 + secs

    #Processing sub_task..the main core function of the project
    def processing_sub_task(self, agent_name, current_prompt, sub_task_number):
        global processing_running, global_responses
        print(f"Starting processing for {agent_name}")

        if processing_running:
            print("Previous processing still running")
            return False

        processing_running = True
        global_responses = ["", "", "", "", ""]
        start_time = time.time()

        try:
            max_attempts = int(self.window['MAX_ATTEMPTS'].get())
            max_time = (int(self.window['TIME_HOURS'].get()) * 3600 +
                        int(self.window['TIME_MINS'].get()) * 60 +
                        int(self.window['TIME_SECS'].get()))

            consecutive_completions = 0
            required_completions = TASK_COMPLETION_CONFIRMATIONS

            provider = self.window["-PROVIDER-"].get()
            model_name = self.window["-MODEL_NAME-"].get()
            model_name, api_key = load_model_config(provider, model_name)
            print(f"Using {provider} with model: {model_name}")

            for attempt in range(1, max_attempts + 1):
                print(f"Attempt {attempt}/{max_attempts}")

                if time.time() - start_time >= max_time:
                    msg = f"Max time ({max_time}s) reached for {agent_name}"
                    print(msg)
                    self.window['-ERROR-'].update(msg)
                    return False

                if stop_event.is_set():
                    msg = f"Agent {agent_name} stopped by user"
                    print(msg)
                    self.window['-ERROR-'].update(msg)
                    return False

                try:
                    pre_prompt = self.agent_executor.get_automated_pre_prompt()
                    minimize_active_window("AGI IN ACTION 1.0")
                    screenshot_path, screenshot_type, cursor_position = capture_and_update_screenshots()
                    print(f"Screenshot captured: {screenshot_type}")

                    agent_content = self.system.load_agent_content(agent_name)
                    full_prompt = self.agent_executor.construct_full_prompt(
                        agent_name, agent_content, pre_prompt,
                        screenshot_path, screenshot_type, global_responses)

                    print(f"Sending request to {provider}")
                    ai_response = self.agent_executor.execute_with_model(
                        provider, model_name, api_key, full_prompt, screenshot_path)
                    print("Received model response")

                    action_results, task_completed = self.agent_executor.process_response(ai_response)
                    print(f"Response processed. Task completed: {task_completed}")

                    if task_completed:
                        consecutive_completions += 1
                        print(f"Completion confirmation: {consecutive_completions}/{required_completions}")
                        if consecutive_completions >= required_completions:
                            print("Task fully completed")
                            return True
                    else:
                        consecutive_completions = 0

                    time.sleep(0.2)

                except Exception as e:
                    error_msg = f"Error in AI response: {str(e)}"
                    print(error_msg)
                    self.window['-ERROR-'].update(error_msg)

        except Exception as e:
            error_msg = f"Error processing {agent_name}: {str(e)}"
            print(error_msg)
            self.window['-ERROR-'].update(error_msg)
        finally:
            processing_running = False

        msg = f"Task not completed: Max attempts/time reached"
        print(msg)
        self.window['-ERROR-'].update(msg)
        return False

    # Function to schedule one time tasks
    async def schedule_one_time(self, agent_name, start_datetime):
        self.stop_flags[agent_name] = False
        self.scheduled_agents[agent_name] = {'next_run': start_datetime, 'interval': 0}
        self.window['-ALL-SCHEDULED-'].update(self.format_scheduled_agents(self.scheduled_agents))
        await self.update_next_scheduled_agent()

        async def agent_work():
            try:
                delay = (start_datetime - datetime.now()).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)

                while not self.stop_flags[agent_name]:
                    current_time = datetime.now()
                    if current_time >= start_datetime:
                        next_agent = min(self.scheduled_agents.items(), key=lambda x: x[1]['next_run'])[0]
                        if next_agent == agent_name and not self.active_agents:
                            self.active_agents[agent_name] = True
                            start_time = datetime.now()
                            self.window['-ACTIVE-'].update(
                                f"{agent_name} (Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')})")

                            self.window['AGENT_LIST'].update(set_to_index=self.system.load_agents().index(agent_name))
                            self.window['CHAT_HISTORY'].update(self.system.load_agent_content(agent_name))

                            threading.Thread(
                                target=self.processing_sub_task,
                                args=(agent_name, self.system.load_agent_content(agent_name),
                                      self.agent_executor.get_sub_task_number(agent_name))
                            ).start()
                            await asyncio.sleep(30)

                            completion_time = datetime.now()
                            self.active_agents.pop(agent_name)
                            self.window['-LAST-'].update(
                                f"{agent_name} (Completed at {completion_time.strftime('%H:%M:%S')})")
                            self.window['-ACTIVE-'].update('None')

                            # Remove after execution
                            self.scheduled_agents.pop(agent_name, None)
                            self.window['-ALL-SCHEDULED-'].update(self.format_scheduled_agents(self.scheduled_agents))
                            break

                    await asyncio.sleep(0.1)

            except Exception as e:
                if not isinstance(e, SystemExit):
                    self.window['-ERROR-'].update(f"Error in {agent_name}: {str(e)}")
            finally:
                if 'e' in locals() and not isinstance(e, SystemExit):
                    self.cleanup_agent(agent_name)

        asyncio.create_task(agent_work())

    # Function to load all timer values at the time of launch of the software
    async def load_all_agent_schedules(self):
        for agent in self.system.load_agents():
            config = self.system.load_agent_config(agent)
            if config:
                interval = config['hours'] * 3600 + config['minutes'] * 60 + config['seconds']
                start_datetime = datetime.now()  # Or parse from config if stored
                await self.run_agent(agent, interval, start_datetime)

    ###Display scheduled Agents
    def format_scheduled_agents(self, scheduled_agents):
        if not scheduled_agents:
            return "None"
        chunks = []
        sorted_agents = sorted(scheduled_agents.items(), key=lambda x: x[1]['next_run'])
        for agent, data in sorted_agents:
            next_run = data['next_run'].strftime('%Y-%m-%d %H:%M:%S')
            agent_text = f"{agent} (Next: {next_run})"
            chunks.append(agent_text)
        return "\n".join(chunks)


    async def handle_agent_creation(self, window, agent_list):
        next_agent_number = 1 if not agent_list else max(
            [int(name[5:]) for name in agent_list if name.startswith("Agent")]) + 1
        current_agent = f"Agent{next_agent_number}"
        agent_list.append(current_agent)
        window['AGENT_LIST'].update(agent_list)
        window['CHAT_HISTORY'].update('')
        return current_agent

    # Update run_agent method
    async def run_agent(self, agent_name, interval, start_datetime):
        self.stop_flags[agent_name] = False
        self.scheduled_agents[agent_name] = {'next_run': start_datetime, 'interval': interval}
        self.window['-ALL-SCHEDULED-'].update(self.format_scheduled_agents(self.scheduled_agents))
        await self.update_next_scheduled_agent()

        async def agent_work():
            try:
                # Wait until start time before beginning execution
                delay = (start_datetime - datetime.now()).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)

                while not self.stop_flags[agent_name]:
                    current_time = datetime.now()
                    scheduled_time = self.scheduled_agents[agent_name]['next_run']
                    if current_time >= scheduled_time:
                        next_agent = min(self.scheduled_agents.items(), key=lambda x: x[1]['next_run'])[0]
                        if next_agent == agent_name:
                            if not self.active_agents:
                                next_run_time = current_time + timedelta(seconds=interval)
                                self.scheduled_agents[agent_name]['next_run'] = next_run_time
                                await self.update_next_scheduled_agent()
                                self.window['-ALL-SCHEDULED-'].update(
                                    self.format_scheduled_agents(self.scheduled_agents))

                                self.window['AGENT_STATUS'].update("")
                                self.active_agents[agent_name] = True
                                start_time = datetime.now()
                                self.window['-ACTIVE-'].update(
                                    f"{agent_name} (Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')})")

                                self.window['AGENT_LIST'].update(
                                    set_to_index=self.system.load_agents().index(agent_name))
                                self.window['CHAT_HISTORY'].update(self.system.load_agent_content(agent_name))

                                # Replace simulation with real execution
                                threading.Thread(
                                    target=self.processing_sub_task,
                                    args=(agent_name, self.system.load_agent_content(agent_name),
                                          self.agent_executor.get_sub_task_number(agent_name))
                                ).start()
                                await asyncio.sleep(30)  # Keep original delay but process real task

                                completion_time = datetime.now()
                                self.active_agents.pop(agent_name)
                                self.window['-LAST-'].update(
                                    f"{agent_name} (Completed at {completion_time.strftime('%H:%M:%S')})")
                                self.window['-ACTIVE-'].update('None')

                    await asyncio.sleep(0.1)

            except Exception as e:
                if not isinstance(e, SystemExit):
                    self.window['-ERROR-'].update(f"Error in {agent_name}: {str(e)}")
            finally:
                if 'e' in locals() and not isinstance(e, SystemExit):
                    self.cleanup_agent(agent_name)

        asyncio.create_task(agent_work())

    async def update_agent_displays(self):
        self.window['-ALL-SCHEDULED-'].update(self.format_scheduled_agents(self.scheduled_agents))
        if self.scheduled_agents:
            next_up = min(self.scheduled_agents.items(), key=lambda x: x[1]['next_run'])
            self.window['-NEXT-'].update(f"{next_up[0]} (Scheduled at: {next_up[1]['next_run'].strftime('%H:%M:%S')})")

    async def execute_agent(self, agent_name):
        try:
            for _ in range(30):
                if self.stop_flags[agent_name]:
                    break
                await asyncio.sleep(0.1)

            completion_time = datetime.now()
            self.active_agents.pop(agent_name, None)
            self.window['-LAST-'].update(f"{agent_name} (Completed at {completion_time.strftime('%H:%M:%S')})")
        except Exception as e:
            if not isinstance(e, SystemExit):
                raise e

    def cleanup_agent(self, agent_name):
        try:
            self.active_agents.pop(agent_name, None)
        except:
            pass

    async def update_next_scheduled_agent(self):
        if self.scheduled_agents:
            next_up = min(self.scheduled_agents.items(), key=lambda x: x[1]['next_run'])
            self.window['-NEXT-'].update(f"{next_up[0]} (Scheduled at: {next_up[1]['next_run'].strftime('%H:%M:%S')})")

    def cancel_agent(self, agent_name):
        if agent_name in self.active_agents:
            self.stop_flags[agent_name] = True
            self.active_agents.pop(agent_name)
            stop_time = datetime.now()
            self.window['-ACTIVE-'].update('None')
            self.window['-LAST-'].update(f"{agent_name} (Stopped by user at {stop_time.strftime('%H:%M:%S')})")
            self.window['AGENT_STATUS'].update("")  # Clear the status

    # ========== MAIN EVENT LOOP REMOVED (NOW INTEGRATED INTO MAIN PROJECT) ==========
    # async def run(self):
    #     # Add this at the start of run()
    #     await self.load_all_agent_schedules()
    #     while True:
    #         event, values = self.window.read(timeout=100)
    #         if event == sg.WINDOW_CLOSED:
    #             break
    #
    #         if event == 'Create Agent':
    #             new_agent = self.system.create_agent("")  # Create empty agent file
    #             self.window['AGENT_LIST'].update(self.system.load_agents())
    #
    #         elif event == 'AGENT_LIST':
    #             if values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 content = self.system.load_agent_content(agent_name)
    #                 self.window['CHAT_HISTORY'].update(content)
    #
    #         elif event == 'Start Agent':
    #             if values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 self.window['AGENT_STATUS'].update(f"{agent_name} Running...")
    #                 stop_event.clear()
    #                 processing_running = False
    #                 threading.Thread(target=self.processing_sub_task,
    #                                  args=(agent_name, self.system.load_agent_content(agent_name),
    #                                        self.agent_executor.get_sub_task_number(agent_name))).start()
    #             else:
    #                 sg.popup("Please select an agent to start.")
    #
    #         elif event == 'Stop Agent':
    #             if values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 stop_event.set()
    #                 processing_running = False
    #                 self.cancel_agent(agent_name)
    #                 self.window['AGENT_STATUS'].update("Agent Stopped")
    #             else:
    #                 sg.popup("No agent is currently selected.")
    #
    #         elif event == 'Save Agent':
    #             if values['AGENT_LIST'] and values['CHAT_HISTORY']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 with open(f"{self.system.agent_folder}/{agent_name}.txt", "w") as f:
    #                     f.write(values['CHAT_HISTORY'])
    #                 sg.popup(f'"{agent_name}" has been updated successfully!!!', title='Update Successful')
    #
    #         elif event == 'Delete Agent':
    #             if values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 self.system.delete_agent(agent_name)
    #                 self.window['AGENT_LIST'].update(self.system.load_agents())
    #
    #         # Add inside the while True loop
    #         elif event == "-SAVE-":
    #             provider = values["-PROVIDER-"]
    #             model_name = values["-MODEL_NAME-"]
    #             api_key = values["-API_KEY-"]
    #             save_api_key(api_key, provider, model_name)
    #             self.window["-SAVED_MODELS-"].update(get_saved_models())
    #             sg.popup(f"API Key and Model Name saved successfully for {provider} - {model_name}")
    #
    #         elif event == "-LOAD-":
    #             selected = values["-SAVED_MODELS-"]
    #             if selected:
    #                 provider, model_name = selected[0].split(" - ")
    #                 loaded_model_name, loaded_api_key = load_model_config(provider, model_name)
    #                 if loaded_model_name and loaded_api_key:
    #                     self.window["-PROVIDER-"].update(provider)
    #                     self.window["-MODEL_NAME-"].update(loaded_model_name)
    #                     self.window["-API_KEY-"].update(loaded_api_key)
    #                     save_last_used_model(provider, loaded_model_name)
    #                     sg.popup(f"Model configuration loaded for {provider} - {model_name}")
    #                 else:
    #                     sg.popup(f"Error: Could not load configuration for {provider} - {model_name}")
    #             else:
    #                 sg.popup("Please select a model from the list before clicking Load.")
    #
    #         elif event == "-REMOVE-":
    #             selected = values["-SAVED_MODELS-"]
    #             if selected:
    #                 provider, model_name = selected[0].split(" - ")
    #                 if remove_model_config(provider, model_name):
    #                     self.window["-SAVED_MODELS-"].update(get_saved_models())
    #                     self.window["-PROVIDER-"].update("")
    #                     self.window["-MODEL_NAME-"].update("")
    #                     self.window["-API_KEY-"].update("")
    #                     sg.popup(f"Model configuration removed for {provider} - {model_name}")
    #                 else:
    #                     sg.popup(f"Error: Could not remove configuration for {provider} - {model_name}")
    #
    #         elif event == 'Send':
    #             user_message = values['CHAT_INPUT'].strip()
    #             if user_message and values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 self.window['CHAT_HISTORY'].update(f"User: {user_message}\n", append=True)
    #                 with open(f"{self.system.agent_folder}/{agent_name}.txt", "a") as f:
    #                     f.write(f"User: {user_message}\n")
    #                 self.window['CHAT_INPUT'].update('')
    #
    #                 threading.Thread(target=self.processing_sub_task,
    #                                  args=(agent_name, user_message,
    #                                        self.agent_executor.get_sub_task_number(agent_name))).start()
    #             elif not values['AGENT_LIST']:
    #                 sg.popup("Please select or create an agent first.")
    #
    #         elif event == '-ONE_TIME-':
    #             self.window['-REPEAT_TEXT-'].update(visible=False)
    #             self.window['HOUR_COMBO'].update(visible=False)
    #             self.window['-HOUR_TEXT-'].update(visible=False)
    #             self.window['MIN_COMBO'].update(visible=False)
    #             self.window['-MIN_TEXT-'].update(visible=False)
    #             self.window['SEC_COMBO'].update(visible=False)
    #             self.window['-SEC_TEXT-'].update(visible=False)
    #
    #         elif event == '-REPEAT-':
    #             self.window['-REPEAT_TEXT-'].update(visible=True)
    #             self.window['HOUR_COMBO'].update(visible=True)
    #             self.window['-HOUR_TEXT-'].update(visible=True)
    #             self.window['MIN_COMBO'].update(visible=True)
    #             self.window['-MIN_TEXT-'].update(visible=True)
    #             self.window['SEC_COMBO'].update(visible=True)
    #             self.window['-SEC_TEXT-'].update(visible=True)
    #
    #         elif event == 'Appoint Agent':
    #             if values['AGENT_LIST']:
    #                 agent_name = values['AGENT_LIST'][0]
    #                 if sg.popup_yes_no(f'Do you want to appoint {agent_name}?', title='Confirm Appointment') == 'Yes':
    #                     try:
    #                         start_date = values['-START_DATE-']
    #                         start_time = f"{values['-START_HOUR-']}:{values['-START_MIN-']}:{values['-START_SEC-']}"
    #                         provider = self.window["-PROVIDER-"].get()
    #                         model_name = self.window["-MODEL_NAME-"].get()
    #
    #                         schedule_type = "one-time" if values['-ONE_TIME-'] else "repeat"
    #                         hours = int(values['HOUR_COMBO'])
    #                         mins = int(values['MIN_COMBO'])
    #                         secs = int(values['SEC_COMBO'])
    #
    #                         self.system.save_agent_config(
    #                             agent_name, schedule_type, start_date, start_time,
    #                             hours, mins, secs, provider, model_name
    #                         )
    #
    #                         start_datetime = datetime.strptime(f"{start_date} {start_time}", '%Y-%m-%d %H:%M:%S')
    #                         if start_datetime <= datetime.now():
    #                             sg.popup('Please select a future date/time', title='Invalid Schedule')
    #                             return
    #
    #                         interval = hours * 3600 + mins * 60 + secs
    #                         if schedule_type == "one-time":
    #                             task = asyncio.create_task(self.schedule_one_time(agent_name, start_datetime))
    #                             self.running_tasks.append(task)
    #                             msg = f'One-time execution scheduled for {start_date} {start_time}'
    #                         else:
    #                             task = asyncio.create_task(self.run_agent(agent_name, interval, start_datetime))
    #                             self.running_tasks.append(task)
    #                             msg = f'Repeated execution scheduled\nFirst run: {start_date} {start_time}\nInterval: {hours}h {mins}m {secs}s'
    #
    #                         sg.popup(
    #                             f'{agent_name} appointment configured\n\n{msg}\n\n'
    #                             f'Model: {model_name}\nProvider: {provider}',
    #                             title='Agent Scheduled'
    #                         )
    #                     except ValueError as e:
    #                         sg.popup(f'Configuration error: {str(e)}', title='Error')
    #
    #         await asyncio.sleep(0.1)


# ========== MAIN EXECUTION REMOVED (NOW INTEGRATED INTO MAIN PROJECT) ==========
# if __name__ == "__main__":
#     gui = GUI()
#     asyncio.run(gui.run())
# ========== END OF REMOVED MAIN EXECUTION ==========