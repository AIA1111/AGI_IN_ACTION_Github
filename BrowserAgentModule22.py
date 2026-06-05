import json
import sys

import PyInstaller
import PySimpleGUI as sg
from cryptography.fernet import Fernet
import re

from markdown_it.common.html_re import attribute
from openai import OpenAI
import base64
import threading
import queue
import google.generativeai as genai
from PIL import Image
import anthropic
from groq import Groq
from playwright.async_api import async_playwright
from together import Together
import os
from datetime import datetime
import time  # Add this import

###Broswer Use imports
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent
import asyncio
import platform
import psutil
import logging
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
from textblob import TextBlob
import nltk

# Platform-specific imports
from platform_utils import get_platform
if get_platform() == "Windows":
    import pygetwindow as gw
    import ctypes
else:
    # macOS/Linux - pygetwindow not needed
    gw = None
    ctypes = None

# Near the top with other imports to use File operations
from FileManager import FileManager
import re  # Add this import line

import os
import shutil
import time
import logging

#Additional imports for chrome driver and for .exe conversion
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
#from webdriver_manager.chrome import ChromeDriverManager  # Don't use webdriver_manager
# Add this with other global variables to keep track of if the AI is currently processing actions or working in ACTION_MODE
is_ai_processing = False

# Initialize encryption
key = b'8jtTR9QcD-dXGDpLLBD8-0jqNjZBfzPHtQcnbYVYfM8='
cipher_suite = Fernet(key)

current_image = None

# Global variables
file_manager = None
default_chrome_path = None

# Global variable to track active task
active_task = None

####IMportant for HITL  START###
import asyncio, threading

# ──────── Module-scope singletons ─────────
_loop = asyncio.new_event_loop()
_thread = threading.Thread(target=_loop.run_forever, daemon=True)
_thread.start()

_browser = None
####IMportant for HITL  END###


# Setup folders
CHAT_MODEL_LIST_FOLDER = "ChatModelList"
os.makedirs(CHAT_MODEL_LIST_FOLDER, exist_ok=True)

def _clone_profile(src_root: str, dest_root: str) -> None:
    """Clone Chrome user data (Local State + Default) from src_root to dest_root."""
    # Copy Local State file (holds DPAPI-encrypted AES key)
    shutil.copy2(
        os.path.join(src_root, "Local State"),
        os.path.join(dest_root, "Local State")
    )
    # Copy Default profile folder, ignoring cache directories
    SKIP = {
        "Cache", "GPUCache", "Service Worker", "Code Cache",
        "IndexedDB", "Local Storage", "Session Storage",
        "Network Action Predictor", "VideoDecodeStats"
    }
    def _ignore(dirpath, names):
        return [n for n in names if n in SKIP]

    shutil.copytree(
        os.path.join(src_root, "Default"),
        os.path.join(dest_root, "Default"),
        dirs_exist_ok=True,
        ignore=_ignore
    )

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def save_api_key(api_key, provider, model_name):
    encrypted_api_key = cipher_suite.encrypt(api_key.encode())
    save_data(encrypted_api_key.decode(), f"{provider}_{model_name}_api_key")
    save_data(model_name, f"{provider}_{model_name}_model_name")
    save_last_used_model(provider, model_name)

def save_data(data, file_name):
    sanitized_file_name = sanitize_filename(file_name)
    full_path = os.path.join(CHAT_MODEL_LIST_FOLDER, f"{sanitized_file_name}.txt")
    with open(full_path, "w") as file:
        file.write(data)

def load_data(file_name):
    try:
        sanitized_file_name = sanitize_filename(file_name)
        with open(os.path.join(CHAT_MODEL_LIST_FOLDER, f"{sanitized_file_name}.txt"), "r") as file:
            return file.read()
    except FileNotFoundError:
        return ""

def get_saved_models():
    saved_models = []
    for filename in os.listdir(CHAT_MODEL_LIST_FOLDER):
        if filename.endswith("_model_name.txt"):
            sanitized_name = filename.rsplit('_model_name.txt', 1)[0]
            provider, model_name = sanitized_name.split('_', 1)
            model_name = model_name.replace('_', '/')
            saved_models.append(f"{provider} - {model_name}")
    return saved_models

def load_api_key(provider, model_name):
    try:
        encrypted_api_key = load_data(f"{provider}_{model_name}_api_key")
        if encrypted_api_key:
            return cipher_suite.decrypt(encrypted_api_key.encode()).decode()
        return ""
    except Exception:
        return ""

def load_model_config(provider, model_name):
    api_key = load_api_key(provider, model_name)
    loaded_model_name = load_data(f"{provider}_{model_name}_model_name")
    return loaded_model_name, api_key

def remove_model_config(provider, model_name):
    try:
        os.remove(os.path.join(CHAT_MODEL_LIST_FOLDER, f"{provider}_{model_name}_api_key.txt"))
        os.remove(os.path.join(CHAT_MODEL_LIST_FOLDER, f"{provider}_{model_name}_model_name.txt"))
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


###Function to save the chat history
def save_chat_history(history, file_name):
    if not os.path.exists("ChatHistory"):
        os.makedirs("ChatHistory")

    # Define the message prefixes
    prefixes = [
        "AI Agent Desktop(",
        "AI Agent Mobile(",
        "User Desktop(",
        "User Mobile("
    ]

    # Split history into interactions
    interactions = []
    current_interaction = []

    for line in history:
        if any(line.startswith(prefix) for prefix in prefixes):
            if current_interaction:
                interactions.append("\n".join(current_interaction))
            current_interaction = [line]
        else:
            current_interaction.append(line)

    if current_interaction:
        interactions.append("\n".join(current_interaction))

    # Keep only the last 1000 interactions
    interactions = interactions[-100:]

    with open(f"ChatHistory/{file_name}.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(interactions))

###Function to Load the chat history
def load_chat_history(file_name):
    try:
        # Define the message prefixes
        prefixes = [
            "AI Agent Desktop(",
            "AI Agent Mobile(",
            "User Desktop(",
            "User Mobile("
        ]

        with open(f"ChatHistory/{file_name}.txt", "r", encoding="utf-8") as file:
            content = file.read()
            interactions = []
            current_lines = []

            for line in content.split('\n'):
                if any(line.startswith(prefix) for prefix in prefixes):
                    if current_lines:
                        interactions.append("\n".join(current_lines))
                    current_lines = [line]
                else:
                    current_lines.append(line)

            if current_lines:
                interactions.append("\n".join(current_lines))

            return interactions[-100:]
    except FileNotFoundError:
        return []

# Save context Memory
def save_context_memory(history):
    if not os.path.exists("ChatHistory"):
        os.makedirs("ChatHistory")

    interactions = []
    current = []

    for line in history[-20:]:
        if line.startswith(("User(", "AI Agent(")):
            if current:
                interactions.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        interactions.append("\n".join(current))

    last_interactions = interactions[-10:]
    with open("ChatHistory/context_memory.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(last_interactions))


def get_context_memory():
    try:
        with open("ChatHistory/context_memory.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

'''
# Add functions to handle Chrome settings
def save_chrome_settings(chrome_path, user_data_path, keep_browser_open):
    if not os.path.exists("Chrome_Config"):
        os.makedirs("Chrome_Config")
    settings = {
        "chrome_path": chrome_path,
        "user_data_path": user_data_path,
        "keep_browser_open": keep_browser_open
    }
    with open("Chrome_Config/chrome_settings.json", "w") as f:
        json.dump(settings, f)

def load_chrome_settings():
    try:
        with open("Chrome_Config/chrome_settings.json", "r") as f:
            settings = json.load(f)
            # Ensure the key exists
            if "keep_browser_open" not in settings:
                settings["keep_browser_open"] = False
            return settings
    except FileNotFoundError:
        return {"chrome_path": "", "user_data_path": "", "keep_browser_open": False}
'''
###Modified code for Chrome Path START###
def save_chrome_settings(chrome_path, user_data_path, keep_browser_open, rolling_window_size=5, dom_refresh_interval=60):
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")
    settings = {
        "chrome_path": chrome_path,
        "user_data_path": user_data_path,
        "keep_browser_open": keep_browser_open,
        "rolling_window_size": rolling_window_size,
        "dom_refresh_interval": dom_refresh_interval
    }
    with open("BrowserSettings/chrome_settings.json", "w") as f:
        json.dump(settings, f, indent=2)

def load_chrome_settings():
    try:
        with open("BrowserSettings/chrome_settings.json", "r") as f:
            settings = json.load(f)
            # Ensure all keys exist with defaults
            if "keep_browser_open" not in settings:
                settings["keep_browser_open"] = False
            if "rolling_window_size" not in settings:
                settings["rolling_window_size"] = 5
            if "dom_refresh_interval" not in settings:
                settings["dom_refresh_interval"] = 60
            return settings
    except FileNotFoundError:
        return {
            "chrome_path": "",
            "user_data_path": "",
            "keep_browser_open": False,
            "rolling_window_size": 5,
            "dom_refresh_interval": 60
        }
###Modified code for Chrome Path END###

#####NEW code FOR EDGE browser Integration START####
###Force code browsers START
def force_close_browsers():
    """
    Force closes any running instances of Edge and Chrome and resets the browser singleton.
    """
    # Reset the browser singleton for HITL mode
    global _browser, _loop

    # Reset the browser singleton if it exists
    if _browser is not None and hasattr(_browser, 'cleanup_browser'):
        try:
            if _loop and _loop.is_running():
                # Use try/except to handle potential issues
                cleanup_fut = asyncio.run_coroutine_threadsafe(
                    _browser.cleanup_browser(),
                    _loop
                )
                # Wait for cleanup with a timeout
                cleanup_fut.result(timeout=5)
                logging.info("Browser singleton cleanup successful")
            _browser = None
            logging.info("Reset browser singleton during cleanup")
        except Exception as e:
            logging.error(f"Error cleaning up browser singleton: {str(e)}")
            _browser = None  # Force reset even if cleanup fails

    # List of browser process names to check (platform-specific)
    # Note: These are lowercase because psutil comparison uses .lower()
    if get_platform() == "Windows":
        browser_processes = [
            'msedge.exe',  # Microsoft Edge
            'chrome.exe',  # Google Chrome
            'chromedriver.exe'  # ChromeDriver
        ]
    elif get_platform() == "Darwin":  # macOS
        browser_processes = [
            'google chrome',  # Chrome on macOS
            'microsoft edge',  # Edge on macOS
            'chromedriver'  # ChromeDriver (no .exe on macOS)
        ]
    elif get_platform() == "Linux":
        browser_processes = [
            'chrome',  # Chrome on Linux
            'chromium',  # Chromium on Linux
            'msedge',  # Edge on Linux
            'microsoft-edge',  # Alternative Edge name
            'chromedriver'  # ChromeDriver
        ]
    else:
        browser_processes = []

    # First check if any browser processes exist
    browser_found = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            process_name = proc.info['name'].lower()
            if any(browser in process_name for browser in browser_processes):
                browser_found = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # If no browsers found, return early without logging
    if not browser_found:
        return 0

    # Only log if browsers were actually found
    logging.info("🔄 Attempting to close running browser instances...")

    closed_count = 0

    # First attempt: Ask processes to close gracefully
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            process_name = proc.info['name'].lower()
            if any(browser in process_name for browser in browser_processes):
                logging.info(f"Closing browser process: {process_name} (PID: {proc.info['pid']})")
                proc.terminate()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Give processes a moment to terminate gracefully
    if closed_count > 0:
        time.sleep(1)

    # Second attempt: Force kill any remaining processes
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            process_name = proc.info['name'].lower()
            if any(browser in process_name for browser in browser_processes):
                logging.info(f"Force killing browser process: {process_name} (PID: {proc.info['pid']})")
                proc.kill()
                closed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Additional Windows-specific cleanup for stubborn processes
    if os.name == 'nt':
        try:
            # Force kill via taskkill (Windows specific)
            for browser in browser_processes:
                subprocess.run(f"taskkill /F /IM {browser}", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logging.error(f"Error during Windows taskkill: {str(e)}")

    # macOS/Linux-specific cleanup
    if get_platform() in ["Darwin", "Linux"]:
        try:
            proc_names = ["Google Chrome", "Microsoft Edge"]
            for proc_name in proc_names:
                subprocess.run(f"pkill -9 -f '{proc_name}'", shell=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("Force killed browser processes via pkill")
        except Exception as e:
            logging.error(f"Error during pkill: {str(e)}")

    # —— NEW: clean up any leftover CDP port & temp profile directory ——
    debug_port = getattr(_browser, 'debug_port', None)
    if debug_port is not None:
        from platform_utils import kill_processes_on_port, wait_for_port_free
        logging.info(f"Killing processes on Debug port....")
        kill_processes_on_port(debug_port)
        wait_for_port_free(debug_port)
        logging.info(f"The debug port has been successfully freed...")

    profile_dir = getattr(_browser, 'profile_dir', None)
    if profile_dir:
        import shutil
        logging.info(f"Deleting temporary profile during clean up....")
        shutil.rmtree(profile_dir, ignore_errors=True)

    if closed_count > 0:
        logging.info(f"Browser cleanup completed. Closed {closed_count} processes.")

    return closed_count

###Force Close Browsers END
def save_edge_settings(edge_path, user_data_path, keep_browser_open, rolling_window_size=5, dom_refresh_interval=60):
    """
    Saves Microsoft Edge settings to a dedicated settings file.

    Args:
        edge_path: Path to Edge executable
        user_data_path: Path to Edge user data directory
        keep_browser_open: Boolean indicating whether to keep browser open after tasks
        rolling_window_size: Number of recent interactions to keep in context
        dom_refresh_interval: Seconds to wait before forcing DOM refresh recovery
    """
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")

    settings = {
        "edge_path": edge_path,
        "user_data_path": user_data_path,
        "keep_browser_open": keep_browser_open,
        "rolling_window_size": rolling_window_size,
        "dom_refresh_interval": dom_refresh_interval
    }

    with open("BrowserSettings/edge_settings.json", "w") as f:
        json.dump(settings, f, indent=2)

    # Also update last used browser file
    save_last_used_browser("Edge")

def save_last_used_browser(browser_type):
    """
    Saves the name of the last used browser to a file.

    Args:
        browser_type: "Chrome" or "Edge"
    """
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")

    with open("BrowserSettings/last_used_browser.txt", "w") as f:
        f.write(browser_type)


def load_last_used_browser():
    """
    Loads the name of the last used browser.

    Returns:
        String containing browser name ("Chrome" or "Edge")
    """
    try:
        with open("BrowserSettings/last_used_browser.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Chrome"  # Default to Chrome if no preference is saved

def save_browser_settings(browser_type, browser_path, user_data_path, keep_browser_open, rolling_window_size=5, dom_refresh_interval=60):
    """
    General function to save settings for the selected browser type.

    Args:
        browser_type: Either "Chrome" or "Edge"
        browser_path: Path to browser executable
        user_data_path: Path to browser user data directory
        keep_browser_open: Boolean indicating whether to keep browser open after tasks
        rolling_window_size: Number of recent interactions to keep in context
        dom_refresh_interval: Seconds to wait before forcing DOM refresh recovery
    """
    # Create the settings directory if it doesn't exist
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")

    if browser_type == "Chrome":
        # Use existing chrome settings function
        save_chrome_settings(browser_path, user_data_path, keep_browser_open, rolling_window_size, dom_refresh_interval)

        # Additionally, save as last used browser
        with open("BrowserSettings/last_used_browser.txt", "w") as f:
            f.write("Chrome")

    elif browser_type == "Edge":
        save_edge_settings(browser_path, user_data_path, keep_browser_open, rolling_window_size, dom_refresh_interval)
    else:
        raise ValueError(f"Unsupported browser type: {browser_type}")


def load_edge_settings():
    """
    Loads Microsoft Edge settings from the settings file.

    Returns:
        Dictionary containing Edge settings with keys:
        "edge_path", "user_data_path", "keep_browser_open",
        "rolling_window_size", and "dom_refresh_interval"
    """
    try:
        with open("BrowserSettings/edge_settings.json", "r") as f:
            settings = json.load(f)

        # Ensure all keys exist with defaults
        if "keep_browser_open" not in settings:
            settings["keep_browser_open"] = False
        if "rolling_window_size" not in settings:
            settings["rolling_window_size"] = 5
        if "dom_refresh_interval" not in settings:
            settings["dom_refresh_interval"] = 60
        # Also update last used browser file
        save_last_used_browser("Edge")

        return settings
    except FileNotFoundError:
        # Return default settings
        return {
            "edge_path": "",
            "user_data_path": "",
            "keep_browser_open": False,
            "rolling_window_size": 5,
            "dom_refresh_interval": 60
        }


###Modified code for RAG Settings START###
def save_rag_settings(memories_per_prompt=50, total_active_missions=15):
    """
    Saves RAG memory configuration settings to memory_config.json (ROOT directory).
    FIXED 2025-12-16: Changed from BrowsingAgent_Config/rag_settings.json to memory_config.json

    Args:
        memories_per_prompt: Number of memories to retrieve per AI prompt (default: 50)
        total_active_missions: Maximum number of active missions allowed (default: 15)
    """
    config_file = "memory_config.json"

    # Load existing config first
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        # If file doesn't exist, start with empty dict
        config = {}

    # Update only the two settings we care about
    config["memories_per_prompt"] = memories_per_prompt
    config["max_active_missions"] = total_active_missions  # Note: using max_active_missions (not total_active_missions)

    # Save back to memory_config.json
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    logging.info(f"✅ RAG settings saved to {config_file}: {memories_per_prompt} memories/prompt, {total_active_missions} max missions")


def load_rag_settings():
    """
    Loads RAG memory configuration settings from memory_config.json (ROOT directory).
    FIXED 2025-12-16: Changed from BrowsingAgent_Config/rag_settings.json to memory_config.json

    Returns:
        Dictionary containing RAG settings with keys:
        "memories_per_prompt", "total_active_missions"
    """
    config_file = "memory_config.json"

    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        # Extract the two settings (with defaults if missing)
        settings = {
            "memories_per_prompt": config.get("memories_per_prompt", 50),
            "total_active_missions": config.get("max_active_missions", 15),  # Note: reading max_active_missions
        }

        return settings
    except FileNotFoundError:
        # Return default settings if config file doesn't exist
        return {
            "memories_per_prompt": 50,
            "total_active_missions": 15,
        }
###Modified code for RAG Settings END###




def load_browser_settings(browser_type=None):
    """
    Loads settings for the specified browser or the last used browser.

    Args:
        browser_type: Either "Chrome", "Edge", or None to use last used browser

    Returns:
        Tuple of (browser_type, settings_dict)
    """
    # Determine which browser to load
    if browser_type is None:
        browser_type = load_last_used_browser()

    # Load settings for the selected browser
    if browser_type == "Chrome":
        return "Chrome", load_chrome_settings()
    elif browser_type == "Edge":
        return "Edge", load_edge_settings()
    else:
        logging.warning(f"Unknown browser type {browser_type}, defaulting to Chrome")
        return "Chrome", load_chrome_settings()

'''
def initialize_browser_settings():
    """Create the initial browser settings files and folders if they don't exist."""

    # Create the BrowserSettings directory if it doesn't exist
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")
        print(f"Created BrowserSettings directory at {os.path.abspath('BrowserSettings')}")

    # Create last_used_browser.txt if it doesn't exist
    last_browser_path = "BrowserSettings/last_used_browser.txt"

    # Get absolute path for better debugging
    abs_path = os.path.abspath(last_browser_path)

    if not os.path.exists(abs_path):
        print(f"Last used browser file not found, creating at: {abs_path}")
        try:
            with open(abs_path, "w") as f:
                f.write("Chrome")
            print("Successfully wrote default 'Chrome' to last used browser file")
        except Exception as e:
            print(f"Error creating last used browser file: {str(e)}")
    else:
        # If file exists, verify it has valid content
        try:
            with open(abs_path, "r") as f:
                content = f.read().strip()
                print(f"Found existing last used browser: '{content}'")

                # Verify content is valid, rewrite if it's empty or invalid
                if content not in ["Chrome", "Edge"]:
                    print(f"Invalid browser name in file: '{content}', resetting to Chrome")
                    with open(abs_path, "w") as f:
                        f.write("Chrome")
        except Exception as e:
            print(f"Error reading existing last used browser file: {str(e)}")
'''

def initialize_browser_settings():
    """Create the initial browser settings files and folders if they don't exist,
    automatically detecting the current username and browser locations."""

    # Create the BrowserSettings directory if it doesn't exist
    if not os.path.exists("BrowserSettings"):
        os.makedirs("BrowserSettings")
        logging.info(f"Created BrowserSettings directory at {os.path.abspath('BrowserSettings')}")

    # Extract username from user's home directory path
    username = os.path.basename(os.path.expanduser("~"))
    logging.info(f"Detected username: {username}")

    # Set up default browser paths
    chrome_settings_path = "BrowserSettings/chrome_settings.json"
    edge_settings_path = "BrowserSettings/edge_settings.json"

    # Define standard locations (these will be overridden if browsers are detected)
    # Platform-specific Chrome paths
    if get_platform() == "Darwin":  # macOS
        standard_chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    elif get_platform() == "Windows":
        standard_chrome_paths = [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
        ]
    elif get_platform() == "Linux":
        standard_chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser"
        ]
    else:
        standard_chrome_paths = []

    # Platform-specific Edge paths
    if get_platform() == "Darwin":  # macOS
        standard_edge_paths = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ]
    elif get_platform() == "Windows":
        standard_edge_paths = [
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe"
        ]
    elif get_platform() == "Linux":
        standard_edge_paths = [
            "/usr/bin/microsoft-edge",
            "/usr/bin/microsoft-edge-stable"
        ]
    else:
        standard_edge_paths = []

    # Default Chrome settings based on platform
    if get_platform() == "Darwin":  # macOS
        chrome_settings = {
            "chrome_path": "",
            "user_data_path": f"/Users/{username}/Library/Application Support/Google/Chrome",
            "keep_browser_open": False
        }
    elif get_platform() == "Windows":
        chrome_settings = {
            "chrome_path": "",
            "user_data_path": f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data",
            "keep_browser_open": False
        }
    elif get_platform() == "Linux":
        chrome_settings = {
            "chrome_path": "",
            "user_data_path": f"/home/{username}/.config/google-chrome",
            "keep_browser_open": False
        }
    else:
        chrome_settings = {
            "chrome_path": "",
            "user_data_path": "",
            "keep_browser_open": False
        }

    # Default Edge settings based on platform
    if get_platform() == "Darwin":  # macOS
        edge_settings = {
            "edge_path": "",
            "user_data_path": f"/Users/{username}/Library/Application Support/Microsoft Edge",
            "keep_browser_open": False
        }
    elif get_platform() == "Windows":
        edge_settings = {
            "edge_path": "",
            "user_data_path": f"C:/Users/{username}/AppData/Local/Microsoft/Edge/User Data",
            "keep_browser_open": False
        }
    elif get_platform() == "Linux":
        edge_settings = {
            "edge_path": "",
            "user_data_path": f"/home/{username}/.config/microsoft-edge",
            "keep_browser_open": False
        }
    else:
        edge_settings = {
            "edge_path": "",
            "user_data_path": "",
            "keep_browser_open": False
        }

    # Try to detect actual browser installations
    for path in standard_chrome_paths:
        if os.path.exists(path):
            chrome_settings["chrome_path"] = path
            logging.info(f"Detected Chrome at: {path}")
            break

    for path in standard_edge_paths:
        if os.path.exists(path):
            edge_settings["edge_path"] = path
            logging.info(f"Detected Edge at: {path}")
            break

    # Save Chrome settings if not already configured
    if not os.path.exists(chrome_settings_path):
        try:
            with open(chrome_settings_path, "w") as f:
                json.dump(chrome_settings, f)
            logging.info("Created default Chrome settings")
        except Exception as e:
            logging.error(f"Error creating Chrome settings file: {str(e)}")

    # Save Edge settings if not already configured
    if not os.path.exists(edge_settings_path):
        try:
            with open(edge_settings_path, "w") as f:
                json.dump(edge_settings, f)
            logging.info("Created default Edge settings")
        except Exception as e:
            logging.error(f"Error creating Edge settings file: {str(e)}")

    # Lastly, ensure last_used_browser.txt exists (keep your existing code)
    last_browser_path = "BrowserSettings/last_used_browser.txt"
    abs_path = os.path.abspath(last_browser_path)

    if not os.path.exists(abs_path):
        logging.info(f"Last used browser file not found, creating at: {abs_path}")
        try:
            with open(abs_path, "w") as f:
                f.write("Chrome")
            logging.info("Successfully wrote default 'Chrome' to last used browser file")
        except Exception as e:
            logging.error(f"Error creating last used browser file: {str(e)}")
    else:
        # If file exists, verify it has valid content
        try:
            with open(abs_path, "r") as f:
                content = f.read().strip()
                logging.info(f"Found existing last used browser: '{content}'")

                # Verify content is valid, rewrite if it's empty or invalid
                if content not in ["Chrome", "Edge"]:
                    logging.warning(f"Invalid browser name in file: '{content}', resetting to Chrome")
                    with open(abs_path, "w") as f:
                        f.write("Chrome")
        except Exception as e:
            logging.error(f"Error reading existing last used browser file: {str(e)}")

def get_default_browser_path(browser_type):
    """
    Returns the default installation path for the specified browser type.

    Args:
        browser_type: Either "Chrome" or "Edge"

    Returns:
        Dictionary with default browser executable and user data paths
    """
    username = os.path.basename(os.path.expanduser("~"))
    platform_name = get_platform()

    if browser_type == "Chrome":
        if platform_name == "Darwin":  # macOS
            return {
                "exe_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "user_data_path": f"/Users/{username}/Library/Application Support/Google/Chrome"
            }
        elif platform_name == "Windows":
            return {
                "exe_path": "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "user_data_path": f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data"
            }
        elif platform_name == "Linux":
            return {
                "exe_path": "/usr/bin/google-chrome",
                "user_data_path": f"/home/{username}/.config/google-chrome"
            }

    elif browser_type == "Edge":
        if platform_name == "Darwin":  # macOS
            return {
                "exe_path": "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "user_data_path": f"/Users/{username}/Library/Application Support/Microsoft Edge"
            }
        elif platform_name == "Windows":
            return {
                "exe_path": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                "user_data_path": f"C:/Users/{username}/AppData/Local/Microsoft/Edge/User Data"
            }
        elif platform_name == "Linux":
            return {
                "exe_path": "/usr/bin/microsoft-edge",
                "user_data_path": f"/home/{username}/.config/microsoft-edge"
            }

    # Default fallback
    return {"exe_path": "", "user_data_path": ""}


def detect_installed_browsers():
    """
    Detects installed browsers and their default paths.

    Returns:
        Dictionary of available browsers with their default paths
    """
    browsers = {}
    platform_name = get_platform()

    if platform_name == "Darwin":  # macOS
        # Check for Chrome
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_path):
            browsers["Chrome"] = chrome_path

        # Check for Edge
        edge_path = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        if os.path.exists(edge_path):
            browsers["Edge"] = edge_path

    elif platform_name == "Windows":
        # Check for Chrome
        chrome_paths = [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                browsers["Chrome"] = path
                break

        # Check for Edge
        edge_paths = [
            "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
            "C:/Program Files/Microsoft/Edge/Application/msedge.exe"
        ]
        for path in edge_paths:
            if os.path.exists(path):
                browsers["Edge"] = path
                break

    elif platform_name == "Linux":
        # Check for Chrome
        chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        for path in chrome_paths:
            if os.path.exists(path):
                browsers["Chrome"] = path
                break

        # Check for Edge
        edge_paths = ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"]
        for path in edge_paths:
            if os.path.exists(path):
                browsers["Edge"] = path
                break

    return browsers

#####NEW code FOR EDGE browser Integration END####

####START:: Additional patch up code for GroqChat for handling Groq requests
# Add this before creating any ChatGroq instances
from langchain_groq.chat_models import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Save the original method
original_create_message_dicts = ChatGroq._create_message_dicts


# Define the patched method with flexible arguments
def patched_create_message_dicts(self, *args, **kwargs):
    # The first argument after self should be the messages
    if len(args) > 0:
        messages = args[0]
    elif 'messages' in kwargs:
        messages = kwargs['messages']
    else:
        # If we can't find messages, just call the original
        return original_create_message_dicts(self, *args, **kwargs)

    # Check if there's an image in any message
    has_image = False
    for msg in messages:
        if hasattr(msg, 'content') and isinstance(msg.content, list):
            for item in msg.content:
                if isinstance(item, dict) and item.get('type') == 'image_url':
                    has_image = True
                    break

    if has_image:
        # If there's an image, combine any system messages into the first human message
        system_content = ""
        new_messages = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_content += msg.content + "\n\n"
            else:
                new_messages.append(msg)

        # If we found system messages, prepend their content to the first human message
        if system_content and new_messages:
            for i, msg in enumerate(new_messages):
                if isinstance(msg, HumanMessage):
                    if isinstance(msg.content, str):
                        new_messages[i] = HumanMessage(content=f"Context: {system_content}\n\n{msg.content}")
                    elif isinstance(msg.content, list):
                        # Handle multimodal content
                        new_content = list(msg.content)
                        for j, item in enumerate(new_content):
                            if isinstance(item, dict) and item.get('type') == 'text':
                                new_content[j] = {
                                    'type': 'text',
                                    'text': f"Context: {system_content}\n\n{item['text']}"
                                }
                                break
                        new_messages[i] = HumanMessage(content=new_content)
                    break

        # If we still have system content but no human message to merge with
        if system_content and not any(isinstance(msg, HumanMessage) for msg in new_messages):
            new_messages.insert(0, HumanMessage(content=f"Context: {system_content}"))

        # Update args or kwargs with our modified messages
        if len(args) > 0:
            new_args = list(args)
            new_args[0] = new_messages
            args = tuple(new_args)
        elif 'messages' in kwargs:
            kwargs['messages'] = new_messages

        # Call the original method with our modified arguments
        return original_create_message_dicts(self, *args, **kwargs)
    else:
        # No images, use the original method as-is
        return original_create_message_dicts(self, *args, **kwargs)


# Apply the patch
ChatGroq._create_message_dicts = patched_create_message_dicts
####END:: Additional patch up code for GroqChat for handling Groq requests


###START:Custom together.ai Adapter for ACTION_MODE to perform browser actions
# — at the top of BrowserAgentModule22.py —

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Type

from together import Together
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, HumanMessage, ToolMessage
# LangChain 1.0 moved output_parsers to langchain_core
from langchain_core.output_parsers import PydanticOutputParser

logger = logging.getLogger("together_adapter")
logger.setLevel(logging.INFO)

class DirectTogetherAdapter:
    """
    Minimal Together.ai adapter for browser_use.Agent.
    - ainvoke(...) to get an AIMessage
    - with_structured_output(...) returning an object with ainvoke(...) -> {'parsed': PydanticModel, 'raw': AIMessage}
    """

    def __init__(self, api_key: str, model: str):
        self.client = Together(api_key=api_key)
        self.model = model

    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        # 1) convert to Together format
        # FIX 2026-01-17: Properly handle AIMessages with tool_calls (previous agent responses)
        payload: List[Dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "system"
                content = msg.content
            elif isinstance(msg, HumanMessage):
                role = "user"
                content = msg.content
            elif isinstance(msg, AIMessage):
                role = "assistant"
                # FIX: AIMessage may have empty content but tool_calls containing the response
                if msg.content:
                    content = msg.content
                elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # FIX 2026-01-17: Extract only the 'args' from tool_calls, not the wrapper
                    import json
                    try:
                        if len(msg.tool_calls) > 0:
                            first_call = msg.tool_calls[0]
                            if isinstance(first_call, dict):
                                args = first_call.get('args', first_call)
                            elif hasattr(first_call, 'args'):
                                args = first_call.args if hasattr(first_call.args, '__dict__') else first_call.args
                            else:
                                args = first_call
                            content = json.dumps(args, indent=2)
                        else:
                            content = ""
                    except Exception:
                        content = str(msg.tool_calls)
                else:
                    content = ""
            elif isinstance(msg, ToolMessage):
                if msg.content and msg.content.strip():
                    role = "user"
                    content = f"[Tool Result]: {msg.content}"
                else:
                    continue
            else:
                continue

            if content:
                payload.append({"role": role, "content": content})

        # 2) call Together synchronously in executor
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=payload,
                max_tokens=1024,
                temperature=0.7,
                top_p=0.7,
                top_k=50,
                repetition_penalty=1.0,
            ),
        )

        # 3) unwrap nested lists & extract .message.content or dict["content"]
        choice = resp.choices[0]
        while isinstance(choice, (list, tuple)):
            choice = choice[0]

        msg_obj = getattr(choice, "message", None) or (choice if isinstance(choice, dict) else None)
        if msg_obj is None:
            raise RuntimeError(f"No message in Together response: {choice}")

        if hasattr(msg_obj, "content"):
            text = msg_obj.content
        else:
            text = msg_obj.get("content", str(msg_obj))

        # 4) wrap in AIMessage
        ai = AIMessage(content=text)
        ai.generations = [[{"text": text}]]
        return ai

    def with_structured_output(
        self,
        schema: Type,
        *,
        include_raw: bool = False,
        method: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Return an object with .ainvoke(messages) -> {'parsed': schema_instance, 'raw': AIMessage}
        so that browser_use.Agent can call it as a structured LLM.
        """
        parser = PydanticOutputParser(pydantic_object=schema)

        async def run_and_parse(messages: List[BaseMessage]):
            ai_msg = await self.ainvoke(messages)
            # parse JSON text into the Pydantic schema
            parsed = parser.parse(ai_msg.content)
            result = {"parsed": parsed}
            if include_raw:
                result["raw"] = ai_msg
            return result

        class Runner:
            def __init__(self, fn):
                self._fn = fn

            async def ainvoke(self, msgs: List[BaseMessage]):
                return await self._fn(msgs)

        return Runner(run_and_parse)


###END:Custom together.ai Adapter for ACTION_MODE to perform browser actions

###START:Custom LM Studio Adapter for ACTION_MODE to perform browser actions
class DirectLMStudioAdapter:
    """
    LM Studio adapter for browser_use.Agent that avoids tool_choice issues.
    Similar to DirectTogetherAdapter but uses OpenAI client with LM Studio endpoint.
    """

    def __init__(self, api_endpoint: str, model: str):
        # Add /v1 if not present
        if not api_endpoint.endswith('/v1'):
            api_endpoint = api_endpoint.rstrip('/') + '/v1'    # For LM Studio, api_key field contains the endpoint which is "http://IP Address:Port" which I have used for simplicity and for copy and

        self.client = OpenAI(api_key="lm-studio", base_url=api_endpoint)
        self.model = model

    async def ainvoke(self, messages: List[BaseMessage]) -> AIMessage:
        # Convert to OpenAI format
        # FIX 2026-01-17: Properly handle AIMessages with tool_calls (previous agent responses)
        # and ToolMessages to ensure LLM can see conversation history
        payload: List[Dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "system"
                content = msg.content
            elif isinstance(msg, HumanMessage):
                role = "user"
                content = msg.content
            elif isinstance(msg, AIMessage):
                role = "assistant"
                # FIX: AIMessage may have empty content but tool_calls containing the response
                # This is how browser_use stores previous agent outputs
                if msg.content:
                    content = msg.content
                elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # FIX 2026-01-17: Extract only the 'args' from tool_calls, not the wrapper
                    # The wrapper format (name, id, type) confuses the LLM into mimicking it
                    import json
                    try:
                        # tool_calls is a list, extract args from first call
                        if len(msg.tool_calls) > 0:
                            first_call = msg.tool_calls[0]
                            # Handle both dict and object formats
                            if isinstance(first_call, dict):
                                args = first_call.get('args', first_call)
                            elif hasattr(first_call, 'args'):
                                args = first_call.args if hasattr(first_call.args, '__dict__') else first_call.args
                            else:
                                args = first_call
                            content = json.dumps(args, indent=2)
                        else:
                            content = ""
                    except Exception as e:
                        # Fallback: just stringify what we have
                        content = str(msg.tool_calls)
                else:
                    content = ""
            elif isinstance(msg, ToolMessage):
                # ToolMessages are typically empty in browser_use, skip them
                # but log if they have content we might want
                if msg.content and msg.content.strip():
                    role = "user"
                    content = f"[Tool Result]: {msg.content}"
                else:
                    continue
            else:
                continue

            # Only add messages with actual content
            if content:
                payload.append({"role": role, "content": content})

        # Call LM Studio synchronously in executor (no tool_choice)
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=payload,
                max_tokens=1000,
                temperature=0.7,
            ),
        )

        text = resp.choices[0].message.content
        ai = AIMessage(content=text)
        ai.generations = [[{"text": text}]]
        return ai

    def with_structured_output(
            self,
            schema: Type,
            *,
            include_raw: bool = False,
            method: Optional[str] = None,
            **kwargs: Any
    ):
        """Return structured output handler for LM Studio"""
        parser = PydanticOutputParser(pydantic_object=schema)

        async def run_and_parse(messages: List[BaseMessage]):
            ai_msg = await self.ainvoke(messages)
            parsed = parser.parse(ai_msg.content)
            result = {"parsed": parsed}
            if include_raw:
                result["raw"] = ai_msg
            return result

        class Runner:
            def __init__(self, fn):
                self._fn = fn

            async def ainvoke(self, msgs: List[BaseMessage]):
                return await self._fn(msgs)

        return Runner(run_and_parse)
###END:Custom LM Studio Adapter for ACTION_MODE to perform browser actions

#############################Extra code to use selenium and locally installed chrome instead of chrome driver START##############
import socket
import subprocess
import time
import asyncio
from selenium import webdriver

def is_port_in_use(port):
    """Return True if the port is in use on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

class BrowserAutomation:
    def __init__(self, api_key, provider="", model_name=""):
        self.provider = provider
        self.model_name = model_name
        ###Modification for MultiBrowser Support START####
        # self.chrome_settings = load_chrome_settings()

        # Get the last used browser
        self.browser_type = load_last_used_browser()

        # Load appropriate browser settings
        if self.browser_type == "Chrome":
            self.browser_settings = load_chrome_settings()
        else:  # Edge
            self.browser_settings = load_edge_settings()
        ###Modification for MultiBrowser Support END####

        self.setup_llm(api_key)
        self.browser = None
        self.browser_context = None
        self.is_interaction_session = False

    def setup_llm(self, api_key):
        if self.provider == "OpenAI":
            self.llm = ChatOpenAI(api_key=api_key, model=self.model_name)
        elif self.provider == "Anthropic":
            self.llm = ChatAnthropic(api_key=api_key, model=self.model_name)
        elif self.provider == "Google":
            self.llm = ChatGoogleGenerativeAI(api_key=api_key, model=self.model_name)
        elif self.provider == "Groq":
            # Use the standard ChatGroq (our patch will be applied)
            self.llm = ChatGroq(api_key=api_key, model=self.model_name)
        elif self.provider == "x.ai":
            # x.ai uses OpenAI-compatible API with a different base URL
            self.llm = ChatOpenAI(api_key=api_key, model=self.model_name, base_url="https://api.x.ai/v1")
        elif self.provider == "Together.ai":
            self.llm = DirectTogetherAdapter(api_key=api_key, model=self.model_name)
        elif self.provider == "LM Studio":
            # Use custom adapter to avoid tool_choice issues
            api_endpoint = api_key  # Contains endpoint URL
            self.llm = DirectLMStudioAdapter(api_endpoint=api_endpoint, model=self.model_name)
        else:
            raise ValueError(f"Provider {self.provider} not supported for browser automation")


    async def get_driver(self):
        # Reuse existing context if in HITL mode
        if self.browser_context and self.is_interaction_session:
            return self.browser_context

        # === Add Chrome/Edge + profile-clone support START ===
        if not self.browser:
            extra_chromium_args = ["--window-size=1920,1080"]

            # Choose exec path key
            browser_path_key = "chrome_path" if self.browser_type == "Chrome" else "edge_path"
            browser_path = self.browser_settings.get(browser_path_key)
            if not browser_path:
                raise ValueError("Browser path must be set in Browser settings.")

            # Instantiate Playwright wrapper
            self.browser = Browser(
                config=BrowserConfig(
                    headless=False,
                    disable_security=False,
                    chrome_instance_path=browser_path,
                    extra_chromium_args=extra_chromium_args,
                )
            )

            # —— persistent profile‐clone support (runs once, then reuses)  ─── clone + one-time interactive login (Windows & Linux) ───
            from platform_utils import normalize_path
            import os
            import shutil
            import time
            import logging
            import subprocess

            # inside your get_driver(), replace the old clone section with:
            user_data_key = "user_data_path"
            base = self.browser_settings.get(user_data_key)
            logging.info(f"🔍 DEBUG: user_data_path from settings = '{base}'")
            logging.info(f"🔍 DEBUG: Current profile_dir (before override) = '{self.browser.profile_dir}'")
            if base:
                # 1) Resolve the real profile root
                name = os.path.basename(base).lower()
                data_root = os.path.dirname(base) if name == "default" else base
                data_root = normalize_path(data_root)  # make OS-correct :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}

                # 2) Define a fixed clone folder beside the real one
                clone_root = normalize_path(os.path.join(data_root, "ClonedProfile"))

                # 3) Clone once if needed
                original_missing = not os.path.isdir(data_root)
                clone_missing = not os.path.isdir(clone_root)

                if not original_missing and clone_missing:
                    start = time.time()
                    logging.info(f"Browser profile Initial clone from {data_root} → {clone_root}")

                    SKIP = {
                        "Cache", "GPUCache", "Service Worker", "Code Cache",
                        "IndexedDB", "Local Storage", "Session Storage",
                        "Network Action Predictor", "VideoDecodeStats"
                    }

                    def _ignore(dirpath, names):
                        return [n for n in names if n in SKIP]

                    shutil.copytree(
                        data_root,
                        clone_root,
                        dirs_exist_ok=True,
                        ignore=_ignore
                    )
                    logging.info(f"Browser profile Clone done in {time.time() - start:.2f}s")

                elif original_missing:
                    logging.warning(f"ORIGINAL Browser profile missing at {data_root}; skipping clone")
                else:
                    logging.info(f"Reusing existing CLONE Browser profile at {clone_root}")

                # 4) One-time GUI login on first clone pass
                if clone_missing and not original_missing:
                    browser_path_key = "chrome_path" if self.browser_type == "Chrome" else "edge_path"
                    exec_path = normalize_path(self.browser_settings[browser_path_key])
                    logging.info("Launching real browser for one-time sign-in…")
                    subprocess.Popen([
                        exec_path,
                        f"--user-data-dir={clone_root}",
                        "--profile-directory=Default",
                        "--no-first-run",
                        "--no-default-browser-check"
                    ]).wait()
                    logging.info("Sign-in complete, continuing with automation.")

                # 5) Point your Browser wrapper at the clone (or fallback)
                self.browser.profile_dir = clone_root if os.path.isdir(clone_root) else data_root
                logging.info(f"🔍 DEBUG: Profile dir SET TO = '{self.browser.profile_dir}'")
        # === Add Chrome/Edge + profile-clone support END ===

        # Create new context if needed
        if not self.browser_context:
            self.browser_context = await self.browser.new_context(
                config=BrowserContextConfig(
                    no_viewport=False,
                    browser_window_size=BrowserContextWindowSize(width=1920, height=1080),
                )
            )

        return self.browser_context


    ####KEY FUNCTION TO PERFORM TASK


    async def execute_task(self, task, values=None):
        # Set processing flag to True at the beginning
        global is_ai_processing
        is_ai_processing = True

        ###This is a optional line to force close all browsers. But by applying this, you can't use HITL mode and so you have to disable this line..So you just apply it once and then, disable it
        #force_close_browsers()

        try:

            ###If values are not defined and then, use default values
            if values is None:
                values = {
                    "-HUMAN_IN_LOOP-": True,
                    "-INFINITE_MEMORY-": False,
                    "-MAX_STEPS-": 1000000,
                    "-KEEP_BROWSER_OPEN-": False
                }

            # Extract values we need
            is_hitl = values.get("-HUMAN_IN_LOOP-", False)
            infinite_memory_enabled = values.get("-INFINITE_MEMORY-", False)  # Define it here
            max_steps = int(values.get("-MAX_STEPS-", 100))

            logging.info(f"Starting task: {task}")

            ### START: Pre-Browser File Command Interceptor ###
            # Check if task contains file commands before sending to browser
            if isinstance(task, str) and ("!file:" in task or "search_google" in str(task) and "!file:" in str(task)):
                # Import re if needed
                import re

                # Process file commands and collect results
                file_results = []

                # Direct file commands
                file_commands = []
                if "!file:" in task:
                    direct_commands = re.findall(r'(!file:[^\n]+(?:\n|$))', task)
                    if not direct_commands:
                        direct_commands = re.findall(r'(!file:[^!]+?)(?=!file:|$)', task, re.DOTALL)
                    file_commands.extend(direct_commands)

                # File commands in search queries
                if "search_google" in str(task) and "!file:" in str(task):
                    # First, extract the entire query string
                    query_matches = re.findall(r'"query":\s*"([^"]*)"', str(task))

                    for query in query_matches:
                        if "!file:" in query:
                            # Extract just the file command including command type and path
                            file_cmd_match = re.search(r'(!file:\w+\s+[\w\/\.]+)', query)
                            if file_cmd_match:
                                clean_cmd = file_cmd_match.group(1).strip()
                                # Remove any trailing characters that aren't part of a valid path
                                clean_cmd = re.sub(r'["\'\}\)\]]+$', '', clean_cmd)
                                file_commands.append(clean_cmd)

                                # Log the extraction for debugging
                                logging.info(f"Extracted file command from query: '{clean_cmd}' from '{query}'")

                # Process each command
                for command in file_commands:
                    # Additional thorough cleaning
                    clean_command = command.strip()
                    # Remove any non-alphanumeric/path characters from the end
                    clean_command = re.sub(r'[^a-zA-Z0-9_\-\/\.\s]+$', '', clean_command)

                    # Log the final command for debugging
                    logging.info(f"Processing file command: '{clean_command}'")

                    try:
                        result = handle_file_command(clean_command[6:].strip())
                        file_results.append(f"✅ {clean_command}: {result}")
                        logging.info(f"Successfully executed file command: '{clean_command}'")
                    except Exception as e:
                        file_results.append(f"❌ {clean_command}: Error - {str(e)}")
                        logging.error(f"Error executing file command in browser task: '{clean_command}' - {str(e)}")

                # If we found and executed file commands, return the results directly
                # without invoking the browser
                if file_results:
                    logging.info(f"Executed {len(file_results)} file commands without browser engagement")
                    return {
                        "done": {
                            "text": "File operations executed:\n\n" + "\n\n".join(file_results)
                        }
                    }
                else:
                    logging.warning("File command patterns detected but no valid commands were extracted")
            ### END: Pre-Browser File Command Interceptor ###

            # Ensure browser is initialized
            if not self.browser:
                await self.get_driver()

            # Ensure browser context is initialized
            if not self.browser_context:
                self.browser_context = await self.browser.new_context()

            # Ensure session is initialized before accessing its attributes
            if not self.browser_context.session:
                await self.browser_context._initialize_session()

            # Configure session handling based on HITL mode
            is_hitl = values.get("-HUMAN_IN_LOOP-", False)
            if is_hitl:
                # Ensure session persistence in HITL mode
                if not self.is_interaction_session:
                    self.is_interaction_session = True
                    if self.browser_context and self.browser_context.session:
                        self.browser_context.session.is_hitl_session = True
                        self.browser_context.session.task_completed = False
                    else:
                        logging.error("Browser session is not initialized correctly.")

                # Ensure we are reusing the same tab in HITL mode
                if self.browser_context.session:
                    self.browser_context.session.current_page = self.browser_context.session.context.pages[0]
                    logging.info(f"HITL Mode: Reusing the same tab - {self.browser_context.session.current_page.url}")

            else:
                logging.info("Not in HITL mode - Opening a new tab.")

            max_steps = int(values.get("-MAX_STEPS-", 100))  # ✅ Read max_steps from GUI input

            # NEW: Read rolling window and DOM refresh settings from GUI
            try:
                rolling_window_size = int(values.get("-ROLLING_WINDOW_SIZE-", "5"))
            except (ValueError, TypeError):
                rolling_window_size = 5  # Default if invalid

            try:
                dom_refresh_interval = int(values.get("-DOM_REFRESH_INTERVAL-", "60"))
            except (ValueError, TypeError):
                dom_refresh_interval = 60  # Default if invalid

            # Prepare agent configuration
            agent_args = {
                "task": task,
                "llm": self.llm,
                "browser": self.browser,
                "browser_context": self.browser_context,
                "human_in_loop": is_hitl,
                "infinite_memory_enabled": infinite_memory_enabled,  # ✅ ADD THIS LINE
                "max_steps": max_steps,  # ✅ Pass max_steps to Agent
                "rolling_window_size": rolling_window_size,  # NEW: Rolling window for context
                "dom_refresh_interval": dom_refresh_interval,  # NEW: DOM refresh timeout
            }

            # Create agent
            agent = Agent(**agent_args)

            # CRITICAL: Store agent instance BEFORE running it (so Stop Agent can access it)
            self.agent = agent
            logging.info("✅ Agent instance stored in browser_module.agent")

            # Set global DOM monitor for GUI display
            try:
                import __main__
                if hasattr(agent, 'dom_monitor'):
                    __main__.global_dom_monitor = agent.dom_monitor
                    logging.info("✅ Global DOM monitor set for GUI display")
                else:
                    logging.warning("⚠️ Agent created but no dom_monitor attribute")
            except Exception as e:
                logging.warning(f"⚠️ Could not set global dom_monitor: {e}")

            # Run agent (this will block until agent completes or is stopped)
            logging.info("🚀 Starting agent.run()...")
            result = await agent.run()
            logging.info("✅ Agent.run() completed")

            # Handle response based on HITL mode
            if self.is_interaction_session:
                self.bring_gui_to_foreground()

                # Check if this is a continuation command
                continuation_commands = ["continue", "proceed", "go ahead", "yes", "done", "complete"]
                if isinstance(task, str) and task.lower().strip() in continuation_commands:
                    if self.browser_context and self.browser_context.session:
                        self.browser_context.session.task_completed = True
                    logging.info("Task explicitly completed by user")
                else:
                    logging.info("Maintaining session for further interaction")

            return result

        except Exception as e:
            logging.error(f"Task failed with error: {str(e)}")
            return {"status": "error", "task": task, "error": str(e)}

        finally:
            # Set processing flag to False before exiting
            #global is_ai_processing....NO need to declare within same scope or function, otherwise, it will show compilation error
            is_ai_processing = False

            # CRITICAL: Reset agent instance after task completes or fails
            if hasattr(self, 'agent'):
                logging.info("🧹 Resetting agent instance in finally block")
                self.agent = None
                # Also reset global DOM monitor
                try:
                    import __main__
                    __main__.global_dom_monitor = None
                    logging.info("✅ Global DOM monitor reset")
                except:
                    pass

            # Handle cleanup based on mode and settings
            if not self.is_interaction_session:
                await self.cleanup_browser()

    def run_task(self, task):
        """Synchronous wrapper for execute_task"""
        return asyncio.run(self.execute_task(task))

   ###Clean up browser and close the browser### FORCE COSE ALL chrome windows
    async def cleanup_browser(self):
        """
        Performs a thorough cleanup of browser resources, including context, browser instance,
        and playwright processes. Also handles any remaining Chrome processes if necessary.
        """
        try:
            # First check if we should keep the browser open
            #if values.get("-KEEP_BROWSER_OPEN-", False):
            #    logging.info("Keeping browser open due to settings")
             #   return

            # Close browser context if it exists
            if self.browser_context:
                await self.browser_context.close()
                logging.info("Browser context closed")
                self.browser_context = None

            # Close browser instance if it exists
            if self.browser:
                await self.browser.close()
                logging.info("Browser closed")
                self.browser = None

            # Stop persistent playwright if it exists
            if hasattr(self, "persistent_playwright") and self.persistent_playwright:
                await self.persistent_playwright.stop()
                logging.info("Playwright stopped")
                self.persistent_playwright = None

            # Add a small delay to allow for graceful shutdown
            await asyncio.sleep(1)

            # Force cleanup of any remaining Chrome processes
            # Note: This should be used carefully as it might affect other Chrome instances
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'].lower()
                if 'chrome' in name:
                    try:
                        proc.kill()
                        logging.info(f"Force killed process: {name}")
                    except Exception as e:
                        logging.error(f"Error killing process {name}: {e}")

            self.is_interaction_session = False
            logging.info("Browser cleanup completed successfully")

        except Exception as e:
            logging.error(f"Error during browser cleanup: {str(e)}")

    '''
    def bring_gui_to_foreground(self):
        try:
            # Window activation only works on Windows
            if gw is not None:
                window_title = "Universal Chat Adapter"
                gui_windows = gw.getWindowsWithTitle(window_title)
            else:
                logging.info("Window activation not available on this platform (non-Windows)")
                gui_windows = []
            if gui_windows:
                window = gui_windows[0]
                hwnd = window._hWnd
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                time.sleep(0.2)
        except Exception as e:
            logging.error(f"Error bringing GUI to foreground: {str(e)}")
    '''

    def bring_gui_to_foreground(self):
        # When used as a module, this can be left empty or made optional
        pass
#############################Extra code to use selenium and locally installed chrome instead of chrome driver END##############

# Threading to run the chat window
class ChatThread(threading.Thread):
   def __init__(self, message, image_path, window, response_queue):
       super().__init__()
       self.message = message
       self.image_path = image_path
       self.window = window
       self.response_queue = response_queue

   def run(self):
       response = chat_completion(self.message, self.image_path)
       self.response_queue.put(response)
       self.window.write_event_value('-CHAT_RESPONSE-', response)

# function to convert the image to base 64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

#########Chat completion code for all providers############

# Individual provider functions
def openai_chat(message, image_path, api_key, model_name):
    client = OpenAI(api_key=api_key)
    base64_image = encode_image(image_path) if image_path else None

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }}
        ] if image_path else message
    }]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=1000
    )
    return response.choices[0].message.content


def google_chat(message, image_path, api_key, model_name):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    if image_path:
        image = Image.open(image_path)
        response = model.generate_content([message, image])
    else:
        response = model.generate_content(message)

    return response.text


def anthropic_chat(message, image_path, api_key, model_name):
    client = anthropic.Anthropic(api_key=api_key)
    base64_image = encode_image(image_path) if image_path else None

    content = [
        {"type": "text", "text": message}
    ]
    if image_path:
        content.insert(0, {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64_image
            }
        })

    response = client.messages.create(
        model=model_name,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text


def xai_chat(message, image_path, api_key, model_name):
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    base64_image = encode_image(image_path) if image_path else None

    content = [{"type": "text", "text": message}]
    if image_path:
        content.insert(0, {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "high"
            }
        })

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": content}],
        temperature=0.01
    )
    return response.choices[0].message.content

'''
def groq_chat(message, image_path, api_key, model_name):
    client = Groq(api_key=api_key)
    base64_image = encode_image(image_path) if image_path else None

    content = [{"type": "text", "text": message}]
    if image_path:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": content}],
        model=model_name
    )
    return response.choices[0].message.content
'''

def groq_chat(message, image_path, api_key, model_name):
    client = Groq(api_key=api_key)
    base64_image = encode_image(image_path) if image_path else None

    # If there's an image, we need to work around Groq's limitation
    # by moving any system prompt into the user message
    if image_path:
        # Extract potential system prompt if present
        if "\n\n" in message:
            parts = message.split("\n\n", 1)
            system_part = parts[0]
            user_part = parts[1]
            # Combine them for Groq since it can't handle system messages with images
            enhanced_message = f"I need you to consider this context: {system_part}\n\nNow regarding this request: {user_part}"
        else:
            enhanced_message = message

        # Add browser context hint to help with screenshots
        enhanced_message = (
                "I'm showing you a screenshot of a webpage to help with browser navigation and understanding. "
                "Please analyze the content and help with the following request: \n\n" + enhanced_message
        )

        content = [{"type": "text", "text": enhanced_message}]
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": content}],
                model=model_name,
                temperature=0.6  # 0.6 temperature is working perfectly fine and good for Groq
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error with Groq processing: {str(e)}"
    else:
        # Without an image, we can use normal message structure with system messages
        try:
            if "\n\n" in message:
                parts = message.split("\n\n", 1)
                system_prompt = parts[0]
                user_message = parts[1]

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            else:
                # No clear system/user separation
                messages = [{"role": "user", "content": message}]

            response = client.chat.completions.create(
                messages=messages,
                model=model_name
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error with Groq text processing: {str(e)}"

def together_chat(message, image_path, api_key, model_name):
    try:
        client = Together(api_key=api_key)  # Pass api_key directly to client
        base64_image = encode_image(image_path) if image_path else None

        content = [{"type": "text", "text": message}]
        if image_path:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": content}],
            max_tokens=512,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stop=["<|eot_id|>", "<|eom_id|>"]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def lm_studio_chat(message, image_path, api_endpoint, model_name):
    # Add /v1 if not present
    if not api_endpoint.endswith('/v1'):
        api_endpoint = api_endpoint.rstrip('/') + '/v1'

    client = OpenAI(api_key="lm-studio", base_url=api_endpoint)
    base64_image = encode_image(image_path) if image_path else None

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }}
        ] if image_path else message
    }]

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=1000
    )
    return response.choices[0].message.content

# Provider mapping
PROVIDER_FUNCTIONS = {
    "OpenAI": openai_chat,
    "Google": google_chat,
    "Anthropic": anthropic_chat,
    "x.ai": xai_chat,
    "Groq": groq_chat,
    "Together.ai": together_chat,
"LM Studio": lm_studio_chat
}

'''
# Main chat completion function
def chat_completion(message, image_path=None):
    provider, model_name = load_last_used_model()
    api_key = load_api_key(provider, model_name)

    system_prompt = values.get("-SYSTEM_PROMPT-", "")
    context = get_context_memory() if values.get("-SEND_CONTEXT-", False) else ""

    browse_mode = values.get("-BROWSE_MODE-")
    if browse_mode:
        browser = BrowserAutomation(api_key, provider, model_name)
        result = browser.run_task(message)

        # Debug print for full result structure
        print("Full result structure:", result)

        # Try to extract the final result
        if isinstance(result, dict) and result['status'] == 'success':
            result_str = str(result['result'])
            if '📄 Result:' in result_str:
                start = result_str.find('📄 Result:') + len('📄 Result:')
                end = result_str.find('\nINFO', start) if '\nINFO' in result_str else len(result_str)
                return f"📄 Result:{result_str[start:end].strip()}\n✅ Task completed successfully"

        return f"❌ Debug - Full result: {str(result)}"

    full_message = f"{system_prompt}\n\nContext:\n{context}\n\nUser Message:\n{message}" if context else f"{system_prompt}\n\n{message}"

    try:
        chat_function = PROVIDER_FUNCTIONS.get(provider)
        if chat_function:
            return chat_function(full_message, image_path, api_key, model_name)
        return f"Provider {provider} not supported"
    except Exception as e:
        return f"Error: {str(e)}"

'''

#####Function to extract AI reply####NOTE::::Verified the extraction two times
import re
import ast

### START: Enhanced AI Message Extraction with File Command Support ###
def extract_ai_message(result):
    """
    1. Convert `result` to a string.
    2. Use a regex to find ALL occurrences of `'done': { ... }` (non-greedily).
    3. Take the LAST match (the final 'done' block).
    4. Parse that block with `ast.literal_eval` (valid Python dict syntax).
    5. Return the `done_dict['text']` string if it exists.
    """

    result_str = str(result)

    # First check for file command results
    if "'done':" in result_str and "File operations executed" in result_str:
        # Try to extract file operation results directly
        file_op_match = re.search(r"File operations executed:\s*(.+?)(?='done':|$)", result_str, re.DOTALL)
        if file_op_match:
            return file_op_match.group(1).strip()

    # Regex to capture anything inside { } after 'done': (including newlines).
    #    - `.*?` is "non-greedy," so it stops at the first matching '}'.
    #    - `re.DOTALL` lets `.` match newlines too.
    pattern = r"'done':\s*(\{.*?\})"

    matches = re.findall(pattern, result_str, flags=re.DOTALL)
    if not matches:
        # Try alternate format that might be used in file operation responses
        alt_pattern = r"'text':\s*'([^']+)'"
        alt_matches = re.findall(alt_pattern, result_str, flags=re.DOTALL)
        if alt_matches:
            return alt_matches[-1].strip()
        return "⚠️ Could not extract a meaningful response from the AI output."

    # Take the *last* 'done' block so we get the final message
    last_done_block = matches[-1].strip()

    # Attempt to parse this block as a Python dictionary, e.g. {'text': '...'}
    # `ast.literal_eval` handles standard Python literal syntax including
    # single-quoted strings, double-quoted strings, etc.
    try:
        done_dict = ast.literal_eval(last_done_block)
        # We expect something like: {'text': '...'}
        text_value = done_dict.get("text", "").strip()

        # Look for file commands in the text and highlight them for visibility
        if "!file:" in text_value:
            # Add highlighting to make file commands more visible
            text_value = re.sub(r'(!file:[^\n]+)', r'【\1】', text_value)

        if text_value:
            return text_value
        else:
            return "⚠️ 'done' block found, but no text key was present."
    except Exception as e:
        # Try to extract anything that looks like it might be the intended output
        fallback_match = re.search(r"'text':\s*'([^']+)", last_done_block)
        if fallback_match:
            return fallback_match.group(1).strip()
        return f"⚠️ Found a 'done' block but could not parse it: {str(e)}"


### END: Enhanced AI Message Extraction with File Command Support ###
'''
###Helper function to resolve path of folders
def resolve_directory(directory):
    """Convert directory names to full paths when needed."""
    if not directory:
        return None

    # Get default paths for mapping directory names
    default_paths = file_manager.get_default_paths()
    dir_mapping = {
        "downloads": default_paths['download_dir'],
        "uploads": default_paths['upload_dir'],
        "common": default_paths['common_dir']
    }

    # Remove trailing slashes
    directory = directory.rstrip('/').rstrip('\\')

    # Log original path for debugging
    logging.info(f"Resolving directory: {directory}")

    # Check if this is a compound path (has directory separators)
    if os.path.sep in directory or '/' in directory:
        # Split at first separator to check if the base directory needs mapping
        parts = re.split(r'[/\\]', directory, 1)
        base_dir = parts[0]
        remaining_path = parts[1] if len(parts) > 1 else ""

        # Check if base directory needs mapping (case-insensitive)
        base_dir_lower = base_dir.lower()
        if base_dir_lower in dir_mapping:
            mapped_path = os.path.join(dir_mapping[base_dir_lower], remaining_path)
            logging.info(f"Mapped compound path: {directory} -> {mapped_path}")
            return mapped_path
    else:
        # Check for simple directory mapping (case-insensitive)
        directory_lower = directory.lower()
        if directory_lower in dir_mapping:
            mapped_path = dir_mapping[directory_lower]
            logging.info(f"Mapped simple path: {directory} -> {mapped_path}")
            return mapped_path

    # If we reach here, no mapping was applied
    logging.info(f"No mapping applied, using original path: {directory}")
    return directory
'''

####Key function to use File Manager
### START: Enhanced File Command Parser with Better Error Handling ###
def handle_file_command(command):
    """Handle file operation commands from the AI."""
    global file_manager

    if file_manager is None:
        return "File manager is not initialized."

    try:
        # Helper function for resolving directory paths
        def resolve_directory(directory):
            """Convert directory names to full paths when needed."""
            if not directory:
                return None

            # Get default paths for mapping directory names
            default_paths = file_manager.get_default_paths()
            dir_mapping = {
                "downloads": default_paths['download_dir'],
                "uploads": default_paths['upload_dir'],
                "common": default_paths['common_dir']
            }

            # Clean the directory path
            # Remove any trailing quotes, braces, etc.
            directory = re.sub(r'["\'\}\)\]]+$', '', directory)

            # Remove trailing slashes
            directory = directory.rstrip('/').rstrip('\\')

            # Log original path for debugging
            logging.info(f"Resolving directory (after cleaning): {directory}")

            # Check if this is a compound path (has directory separators)
            if os.path.sep in directory or '/' in directory:
                # Split at first separator to check if the base directory needs mapping
                parts = re.split(r'[/\\]', directory, 1)
                base_dir = parts[0]
                remaining_path = parts[1] if len(parts) > 1 else ""

                # Check if base directory needs mapping (case-insensitive)
                base_dir_lower = base_dir.lower()
                if base_dir_lower in dir_mapping:
                    mapped_path = os.path.join(dir_mapping[base_dir_lower], remaining_path)
                    logging.info(f"Mapped compound path: {directory} -> {mapped_path}")
                    return mapped_path
            else:
                # Check for simple directory mapping (case-insensitive)
                directory_lower = directory.lower()
                if directory_lower in dir_mapping:
                    mapped_path = dir_mapping[directory_lower]
                    logging.info(f"Mapped simple path: {directory} -> {mapped_path}")
                    return mapped_path

            # If we reach here, no mapping was applied
            logging.info(f"No mapping applied, using original path: {directory}")
            return directory

        # Parse the command
        if not command or len(command.strip()) == 0:
            return "Error: Empty command"

        parts = command.split(" ", 1)
        operation = parts[0].lower().strip()

        # LIST operation
        if operation == "list":
            # List files in a directory
            directory = parts[1] if len(parts) > 1 else None
            directory = resolve_directory(directory)

            files = file_manager.list_files(directory)
            if not files:
                return f"No files found in {directory or 'any directory'}"

            return f"Found {len(files)} files:\n" + "\n".join([f"- {f['name']} ({f['size']} bytes)" for f in files])

        # READ operation
        elif operation == "read":
            # Read file content
            if len(parts) < 2:
                return "Error: Missing file path. Usage: !file:read filepath"

            filepath = parts[1].strip()
            filepath = resolve_directory(filepath)

            content = file_manager.get_file_content(filepath)
            if content:
                preview = content[:1000] + "..." if len(content) > 1000 else content
                return f"Content of {filepath}:\n\n{preview}"
            return f"Error: Could not read {filepath}"

        # WRITE operation with improved parsing
        elif operation == "write":
            # Format: write filename|content
            if len(parts) < 2:
                return "Error: Write format should be 'write filename|content'"

            # Handle case where | might not be the first delimiter in the string
            write_parts = parts[1].split("|", 1)
            if len(write_parts) < 2:
                return "Error: Write format requires a | character to separate filename and content"

            filename, content = write_parts
            filename = filename.strip()
            filename = resolve_directory(filename)

            # Clean up content by removing trailing JSON syntax artifacts
            content = content.strip()
            # Remove trailing '}}', '}"]', '}"', etc. that might come from JSON formatting
            content = re.sub(r'["\'\}\)\]]+$', '', content)

            success = file_manager.write_file(filename, content)

            if success:
                return f"Successfully wrote to {filename}"
            return f"Error writing to {filename}"

        # MOVE operation
        elif operation == "move":
            # Format: move source to destination
            if len(parts) < 2:
                return "Error: Move format should be 'move source to destination'"

            # Enhanced parsing to handle paths with spaces
            if " to " not in parts[1]:
                return "Error: Move format requires 'to' keyword between source and destination"

            source, destination = parts[1].split(" to ", 1)
            source = source.strip()
            destination = destination.strip()
            source = resolve_directory(source)

            # Check for special destination keywords
            if destination.lower() == "uploads":
                result = file_manager.move_to_uploads(source)
                return f"Moved {source} to uploads folder: {result}" if result else f"Failed to move {source} to uploads"
            elif destination.lower() == "downloads":
                result = file_manager.move_to_downloads(source)
                return f"Moved {source} to downloads folder: {result}" if result else f"Failed to move {source} to downloads"
            elif destination.lower() == "common":
                result = file_manager.move_to_common(source)
                return f"Moved {source} to common folder: {result}" if result else f"Failed to move {source} to common"
            else:
                # Custom destination
                destination = resolve_directory(destination)
                success = file_manager.copy_file(source, destination)
                if success:
                    file_manager.delete_file(source)
                    return f"Moved {source} to {destination}"
                return f"Failed to move {source} to {destination}"

        # Additional operations with enhanced parsing for edge cases
        elif operation == "copy":
            if len(parts) < 2 or " to " not in parts[1]:
                return "Error: Copy format should be 'copy source to destination'"

            source, destination = parts[1].split(" to ", 1)
            source = resolve_directory(source.strip())
            destination = resolve_directory(destination.strip())

            success = file_manager.copy_file(source, destination)
            return f"Copied {source} to {destination}" if success else f"Failed to copy {source} to {destination}"

        elif operation == "delete":
            if len(parts) < 2:
                return "Error: Delete format should be 'delete filepath'"

            filepath = parts[1].strip()
            filepath = resolve_directory(filepath)

            success = file_manager.delete_file(filepath)
            return f"Deleted {filepath}" if success else f"Failed to delete {filepath}"

        elif operation == "search":
            if len(parts) < 2:
                return "Error: Search format should be 'search query [in directory]'"

            # Handle the "in directory" part more robustly
            if " in " in parts[1]:
                query, directory = parts[1].split(" in ", 1)
                query = query.strip()
                directory = resolve_directory(directory.strip())
            else:
                query = parts[1].strip()
                directory = None

            files = file_manager.search_files(query, directory)
            if files:
                return f"Found {len(files)} files matching '{query}':\n" + "\n".join([f"- {f['name']}" for f in files])
            return f"No files found matching '{query}'"

        elif operation == "recent":
            # Parse more carefully
            if len(parts) <= 1:
                count = 10
                directory = None
            else:
                remaining = parts[1].strip()
                # Try to extract count if present
                try:
                    if remaining.split()[0].isdigit():
                        count = int(remaining.split()[0])
                        remaining = " ".join(remaining.split()[1:])
                    else:
                        count = 10
                except:
                    count = 10

                # See if there's a directory specified
                if " in " in remaining:
                    directory = remaining.split(" in ", 1)[1].strip()
                    directory = resolve_directory(directory)
                else:
                    directory = resolve_directory(remaining) if remaining else None

            files = file_manager.get_recent_files(count, directory)
            if files:
                return f"{len(files)} most recent files:\n" + "\n".join(
                    [f"- {f['name']} (modified: {f['modified']})" for f in files])
            return "No files found"

        elif operation == "extension":
            if len(parts) < 2:
                return "Error: Extension format should be 'extension .ext [in directory]'"

            # Enhanced parsing
            if " in " in parts[1]:
                extension, directory = parts[1].split(" in ", 1)
                extension = extension.strip()
                directory = resolve_directory(directory.strip())
            else:
                extension = parts[1].strip()
                directory = None

            if not extension.startswith("."):
                extension = "." + extension

            files = file_manager.find_files_by_extension(extension, directory)
            if files:
                return f"Found {len(files)} files with extension '{extension}':\n" + "\n".join(
                    [f"- {f['name']}" for f in files])
            return f"No files found with extension '{extension}'"

        elif operation == "paths":
            paths = file_manager.get_default_paths()
            return "File Manager Paths:\n" + "\n".join([f"- {k}: {v}" for k, v in paths.items()])

        else:
            return f"Unknown file operation: {operation}\n\nAvailable commands:\n" + \
                "- list [directory]\n" + \
                "- read filepath\n" + \
                "- write filename|content\n" + \
                "- move source to destination\n" + \
                "- copy source to destination\n" + \
                "- delete filepath\n" + \
                "- search query [in directory]\n" + \
                "- recent [count] [in directory]\n" + \
                "- extension .ext [in directory]\n" + \
                "- paths"

    except Exception as e:
        logging.error(f"Error in file command processing: {str(e)}")
        return f"Error processing file command: {str(e)}"

### END: Enhanced File Command Parser with Better Error Handling ###


# Main chat completion function###############IMPORTANT NOTE::The issue with extraction of response was in chat_completion code which was fixed
def chat_completion(message, image_path=None):
    """
    Example of a 'chat_completion' function that always calls extract_ai_message
    for the browsing scenario to ensure we only show the final 'done' text.
    """
    # Check if this is a file command
    if message.startswith("!file:"):
        return handle_file_command(message[6:].strip())

    provider, model_name = load_last_used_model()
    api_key = load_api_key(provider, model_name)

    #browse_mode = values.get("-BROWSE_MODE-")

    browse_mode=None

    if browse_mode:
        browser = BrowserAutomation(api_key, provider, model_name)
        try:
            # 'result' could be ANY type (dict, list, custom object). We don't care:
            # we always feed it into extract_ai_message.
            result = browser.run_task(message)

            # If 'result' is a dict with 'status' == 'waiting', you might do something else:
            if isinstance(result, dict) and result.get("status") == "waiting":
                browser.bring_gui_to_foreground()

            # The key fix: ALWAYS parse the AI's response, no matter what.
            return extract_ai_message(result)

        except Exception as e:
            return f"Error: {str(e)}"

    # ----- Non-browsing scenario: standard chat completion -----



# Initialize browser variable
browser = None

###START: File Manager code
# Initialize file manager
file_manager = FileManager()

# Try to determine Chrome download directory from settings
chrome_download_dir = None
chrome_settings = load_chrome_settings()
if chrome_settings and "chrome_path" in chrome_settings:
    # Try to get download directory from user data path
    if "user_data_path" in chrome_settings and chrome_settings["user_data_path"]:
        # Try to locate Downloads relative to user data path
        potential_download_dir = os.path.join(chrome_settings["user_data_path"], "..", "Downloads")
        if os.path.exists(potential_download_dir):
            chrome_download_dir = potential_download_dir

    # If still not found, try standard user Downloads folder
    if not chrome_download_dir:
        potential_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(potential_download_dir):
            chrome_download_dir = potential_download_dir

# Start file monitoring
file_manager.start_monitoring(chrome_download_dir)
logging.info(
    f"File manager initialized with download directory: {chrome_download_dir if chrome_download_dir else 'None'}")
###END: File Manager Code

# Main entry point for browser tasks...MOST IMPORTANT: This is most important for browser tasks
def execute_browser_task(
    message,
    api_key,
    provider,
    model_name,
    image_path=None,
    human_in_loop=True,
    infinite_memory=False,
    max_steps=1000000,
    keep_browser_open=False,
    rolling_window_size=5,  # NEW: Rolling window size for context
    dom_refresh_interval=60  # NEW: DOM refresh interval in seconds
):
    """
    Main entry point for browser tasks. Reuses the same BrowserAutomation
    instance (and underlying Playwright session) across calls on a
    dedicated asyncio loop.
    """
    global _browser, _loop

    # 1) Instantiate & init via get_driver() once
    if _browser is None:
        _browser = BrowserAutomation(api_key, provider, model_name)
        init_fut = asyncio.run_coroutine_threadsafe(
            _browser.get_driver(),
            _loop
        )
        # Blocks until the browser (and context) are actually up
        init_fut.result()

    # 2) Build the values dict
    values = {
        "-HUMAN_IN_LOOP-": human_in_loop,
        "-INFINITE_MEMORY-": infinite_memory,
        "-MAX_STEPS-": max_steps,
        "-KEEP_BROWSER_OPEN-": keep_browser_open,
        "-ROLLING_WINDOW_SIZE-": rolling_window_size,  # NEW: Pass rolling window size
        "-DOM_REFRESH_INTERVAL-": dom_refresh_interval  # NEW: Pass DOM refresh interval
    }

    # 3) Dispatch the actual task onto the same loop
    task_fut = asyncio.run_coroutine_threadsafe(
        _browser.execute_task(message, values),
        _loop
    )
    result = task_fut.result()  # waits here until done

    # 4) Extract and return the assistant’s reply
    return extract_ai_message(result)



def initialize(chrome_path=None, user_data_path=None):
    """
    Initialize the browser module with required settings and resources.

    This function should be called once before using any browser functionality.
    It sets up logging, initializes the file manager, and configures paths.

    Args:
        chrome_path (str, optional): Path to Chrome executable
        user_data_path (str, optional): Path to Chrome user data directory

    Returns:
        bool: True if initialization was successful
    """
    # Initialize logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Initialize file manager
    global file_manager
    file_manager = FileManager()

    # Start file monitoring
    chrome_download_dir = None
    if user_data_path:
        potential_download_dir = os.path.join(user_data_path, "..", "Downloads")
        if os.path.exists(potential_download_dir):
            chrome_download_dir = potential_download_dir

    if not chrome_download_dir:
        potential_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(potential_download_dir):
            chrome_download_dir = potential_download_dir

    file_manager.start_monitoring(chrome_download_dir)
    logging.info(f"File manager initialized with download directory: {chrome_download_dir}")

    # Store chrome path for future use
    global default_chrome_path
    default_chrome_path = chrome_path

    return True


def cleanup():
    """
    Clean up resources used by the browser module.

    This function should be called when the application is shutting down
    to ensure all resources are properly released.

    Returns:
        bool: True if cleanup was successful
    """
    global file_manager
    if file_manager:
        try:
            file_manager.cleanup()
            logging.info("File manager cleanup completed")
        except Exception as e:
            logging.error(f"Error during file manager cleanup: {str(e)}")

    # Add any other cleanup operations here

    logging.info("Browser module cleanup completed")
    return True