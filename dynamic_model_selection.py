"""
Dynamic Model Selection Module

Provides automatic model switching strategies for AGI IN ACTION system.
Completely isolated module - all model switching logic contained here.

Strategies:
- Fixed: No switching (default)
- Alternative: Alternate between 2 models after each reply
- Probabilistic: Random weighted selection (e.g., 70% Model A, 30% Model B)

Author: AGI IN ACTION Team
Date: 2025-12-04
"""

import os
import json
import random
import logging
from datetime import datetime

# Use the same logger as main application
logger = logging.getLogger(__name__)

# File paths
SETTINGS_FILE = os.path.join("GeneralSettings", "ModelSwitchingSettings.json")
CHAT_MODEL_DIR = "ChatModelList"

# Model file mappings
MODEL_FILES = {
    "CHAT_MODE": {
        "last_used": os.path.join(CHAT_MODEL_DIR, "last_used_chat_model.txt"),
        "alternate": os.path.join(CHAT_MODEL_DIR, "alternate_chat_model.txt")
    },
    "ACTION_MODE": {
        "last_used": os.path.join(CHAT_MODEL_DIR, "last_used_action_model.txt"),
        "alternate": os.path.join(CHAT_MODEL_DIR, "alternate_action_model.txt")
    }
}


def load_switching_settings():
    """
    Loads model switching configuration from JSON file.

    Returns:
        dict: {
            "strategy": "Fixed" | "Alternative" | "Probabilistic",
            "probability_percent": int (1-100)
        }

    Default: {"strategy": "Fixed", "probability_percent": 70}
    """
    default_settings = {
        "strategy": "Fixed",
        "probability_percent": 70
    }

    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            logger.debug(f"Loaded switching settings: {settings}")
            return settings
        else:
            logger.info("Switching settings file not found, using defaults")
            return default_settings
    except Exception as e:
        logger.error(f"Error loading switching settings: {e}")
        return default_settings


def save_switching_settings(strategy, probability):
    """
    Saves model switching configuration to JSON file.

    Args:
        strategy (str): "Fixed", "Alternative", or "Probabilistic"
        probability (int): Percentage 1-100 (only used for Probabilistic)

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure GeneralSettings directory exists
        os.makedirs("GeneralSettings", exist_ok=True)

        settings = {
            "strategy": strategy,
            "probability_percent": int(probability)
        }

        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)

        logger.info(f"Saved switching settings: {strategy}, probability={probability}%")
        return True

    except Exception as e:
        logger.error(f"Error saving switching settings: {e}")
        return False


def validate_alternate_model_exists(mode):
    """
    Checks if alternate model file exists and is valid.

    Args:
        mode (str): "CHAT_MODE" or "ACTION_MODE"

    Returns:
        bool: True if alternate file exists and not empty
    """
    if mode not in MODEL_FILES:
        logger.error(f"Invalid mode: {mode}")
        return False

    alternate_file = MODEL_FILES[mode]["alternate"]

    try:
        if not os.path.exists(alternate_file):
            logger.warning(f"Alternate model file not found: {alternate_file}")
            return False

        # Check if file has content
        with open(alternate_file, 'r') as f:
            content = f.read().strip()

        if not content:
            logger.warning(f"Alternate model file is empty: {alternate_file}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating alternate model file: {e}")
        return False


def get_model_name_from_file(filepath):
    """
    Reads model name from file for display purposes.

    Args:
        filepath (str): Path to model file

    Returns:
        str: Model name or "Unknown" if error
    """
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                model_name = f.read().strip()
            return model_name if model_name else "Unknown"
        else:
            return "Unknown"
    except Exception as e:
        logger.error(f"Error reading model name from {filepath}: {e}")
        return "Unknown"


def swap_model_files(mode):
    """
    Swaps last_used_* ↔ alternate_* files atomically.

    Args:
        mode (str): "CHAT_MODE" or "ACTION_MODE"

    Returns:
        tuple: (old_model_name, new_model_name)

    Raises:
        Exception: If swap operation fails
    """
    if mode not in MODEL_FILES:
        raise ValueError(f"Invalid mode: {mode}")

    last_used_file = MODEL_FILES[mode]["last_used"]
    alternate_file = MODEL_FILES[mode]["alternate"]

    try:
        # Read both files
        with open(last_used_file, 'r') as f:
            last_used_content = f.read().strip()

        with open(alternate_file, 'r') as f:
            alternate_content = f.read().strip()

        # Swap contents atomically
        with open(last_used_file, 'w') as f:
            f.write(alternate_content)

        with open(alternate_file, 'w') as f:
            f.write(last_used_content)

        logger.info(f"[{mode}] Swapped models: {last_used_content} → {alternate_content}")

        return (last_used_content, alternate_content)

    except Exception as e:
        logger.error(f"Failed to swap model files for {mode}: {e}")
        raise


def refresh_gui_models(window, model_manager):
    """
    Refreshes the GUI model display after switching.

    Args:
        window: PySimpleGUI window object
        model_manager: ModelManager instance to load current models
    """
    try:
        if not window:
            logger.warning("[GUI REFRESH] No window provided, skipping GUI refresh")
            return

        logger.info("[GUI REFRESH] Starting model display refresh...")

        # Get the current models for each mode
        chat_provider, chat_model = model_manager.load_last_used_model("CHAT_MODE")
        logger.info(f"[GUI REFRESH] Loaded CHAT_MODE: {chat_provider} - {chat_model}")

        action_provider, action_model = model_manager.load_last_used_model("ACTION_MODE")
        logger.info(f"[GUI REFRESH] Loaded ACTION_MODE: {action_provider} - {action_model}")

        # Update the display for CHAT_MODE
        if chat_provider and chat_model:
            window["-CURRENT_CHAT_MODEL-"].update(f"{chat_provider} - {chat_model}", text_color="blue")
            logger.info(f"[GUI REFRESH] Updated CHAT_MODE display to: {chat_provider} - {chat_model}")
        else:
            window["-CURRENT_CHAT_MODEL-"].update("Not loaded", text_color="blue")
            logger.warning("[GUI REFRESH] CHAT_MODE not loaded")

        # Update the display for ACTION_MODE
        if action_provider and action_model:
            window["-CURRENT_ACTION_MODEL-"].update(f"{action_provider} - {action_model}", text_color="orange")
            logger.info(f"[GUI REFRESH] Updated ACTION_MODE display to: {action_provider} - {action_model}")
        else:
            window["-CURRENT_ACTION_MODEL-"].update("Not loaded", text_color="orange")
            logger.warning("[GUI REFRESH] ACTION_MODE not loaded")

        logger.info("[GUI REFRESH] Model display refresh completed successfully")

    except Exception as e:
        logger.error(f"[GUI REFRESH] Failed to update model display: {e}")
        import traceback
        logger.error(f"[GUI REFRESH] Traceback: {traceback.format_exc()}")


def execute_model_switching(mode, window=None, model_manager=None):
    """
    MAIN ENTRY POINT - Called after RAG memory update.

    Executes model switching based on configured strategy.
    CRITICAL: Always swaps BOTH CHAT_MODE and ACTION_MODE models together.

    Args:
        mode (str): "CHAT_MODE" or "ACTION_MODE" (kept for backward compatibility, but BOTH modes always switch)
        window: PySimpleGUI window object (None for Android/headless)
        model_manager: ModelManager instance (optional, for GUI refresh)

    Logic Flow:
        1. Load settings (strategy, probability)
        2. If strategy == "Fixed" → EXIT immediately (no processing)
        3. Validate alternate models exist for BOTH modes
        4. Execute strategy:
            - Alternative: Always swap BOTH modes
            - Probabilistic: Swap BOTH modes if random(1-100) > probability
        5. Show confirmation popup (Desktop only) - displays BOTH model changes
        6. Refresh GUI model display (Desktop only) - updates BOTH mode displays
        7. Log to CLI

    Returns:
        None
    """
    try:
        # Load settings
        settings = load_switching_settings()
        strategy = settings.get('strategy', 'Fixed')

        # CRITICAL: If Fixed, exit immediately (zero overhead)
        if strategy == "Fixed":
            return

        # Validate alternate models exist for BOTH modes
        chat_exists = validate_alternate_model_exists("CHAT_MODE")
        action_exists = validate_alternate_model_exists("ACTION_MODE")

        if not chat_exists or not action_exists:
            missing_modes = []
            if not chat_exists:
                missing_modes.append("CHAT_MODE")
            if not action_exists:
                missing_modes.append("ACTION_MODE")

            logger.warning(f"Alternate models not configured for: {', '.join(missing_modes)}, skipping switch")
            if window:
                try:
                    import PySimpleGUI as sg
                    sg.popup_quick_message(
                        f"⚠️ Alternate models missing for:\n{', '.join(missing_modes)}\n\nBoth CHAT_MODE and ACTION_MODE\nalternate models are required!",
                        background_color='orange',
                        text_color='white',
                        auto_close_duration=4,
                        font=('Helvetica', 11)
                    )
                    logger.info("[VALIDATION] Warning popup displayed")
                except Exception as popup_error:
                    logger.error(f"[VALIDATION] Warning popup failed: {popup_error}")
            return

        # Execute strategy
        if strategy == "Alternative":
            # Always swap BOTH modes for Alternative strategy
            try:
                # Swap CHAT_MODE
                chat_old, chat_new = swap_model_files("CHAT_MODE")
                logger.info(f"[ALTERNATIVE] CHAT_MODE: {chat_old} → {chat_new}")

                # Swap ACTION_MODE
                action_old, action_new = swap_model_files("ACTION_MODE")
                logger.info(f"[ALTERNATIVE] ACTION_MODE: {action_old} → {action_new}")

                # Show confirmation popup (Desktop only)
                if window:
                    try:
                        import PySimpleGUI as sg
                        sg.popup_quick_message(
                            f"🔄 Models Switched\nCHAT: {chat_old} → {chat_new}\nACTION: {action_old} → {action_new}",
                            background_color='blue',
                            text_color='white',
                            auto_close_duration=5,
                            font=('Helvetica', 11)
                        )
                        logger.info("[ALTERNATIVE] Popup displayed successfully")
                    except Exception as popup_error:
                        logger.error(f"[ALTERNATIVE] Popup failed: {popup_error}")

                    # Refresh GUI model display
                    if model_manager:
                        refresh_gui_models(window, model_manager)
                        logger.info("[ALTERNATIVE] GUI refreshed successfully")
                    else:
                        logger.warning("[ALTERNATIVE] model_manager not provided, GUI not refreshed")

            except Exception as e:
                logger.error(f"[ALTERNATIVE] Failed to swap models: {e}")

        elif strategy == "Probabilistic":
            # Probabilistic strategy - SIMPLIFIED
            # Probability represents % chance to SWITCH (e.g., 70 = 70% chance to switch)
            probability = settings.get('probability_percent', 70)
            random_num = random.randint(1, 100)

            logger.info(f"[PROBABILISTIC] Rolling dice: {random_num} out of 100, probability threshold: {probability}%")

            # SIMPLE LOGIC: If random <= probability, SWITCH
            # Example: probability=70 means switch if random is 1-70 (70% chance)
            if random_num <= probability:
                logger.info(f"[PROBABILISTIC] {random_num} <= {probability}, SWITCHING models")
                try:
                    # Swap BOTH modes
                    chat_old, chat_new = swap_model_files("CHAT_MODE")
                    logger.info(f"[PROBABILISTIC] CHAT_MODE: {chat_old} → {chat_new}")

                    action_old, action_new = swap_model_files("ACTION_MODE")
                    logger.info(f"[PROBABILISTIC] ACTION_MODE: {action_old} → {action_new}")

                    # Show confirmation popup (Desktop only)
                    if window:
                        try:
                            import PySimpleGUI as sg
                            sg.popup_quick_message(
                                f"🎲 Models Switched [Roll: {random_num} ≤ {probability}%]\nCHAT: {chat_old} → {chat_new}\nACTION: {action_old} → {action_new}",
                                background_color='purple',
                                text_color='white',
                                auto_close_duration=5,
                                font=('Helvetica', 11)
                            )
                            logger.info("[PROBABILISTIC] Popup displayed successfully")
                        except Exception as popup_error:
                            logger.error(f"[PROBABILISTIC] Popup failed: {popup_error}")

                        # Refresh GUI model display
                        if model_manager:
                            refresh_gui_models(window, model_manager)
                            logger.info("[PROBABILISTIC] GUI refreshed successfully")
                        else:
                            logger.warning("[PROBABILISTIC] model_manager not provided, GUI not refreshed")

                except Exception as e:
                    logger.error(f"[PROBABILISTIC] Failed to swap models: {e}")
            else:
                # Keep current models - NO SWITCH
                logger.info(f"[PROBABILISTIC] {random_num} > {probability}, KEEPING current models (no switch)")

        else:
            logger.warning(f"Unknown strategy: {strategy}")

    except Exception as e:
        logger.error(f"Error in execute_model_switching for {mode}: {e}")
        # Don't raise - graceful failure


# Module self-test (run only when executed directly)
if __name__ == "__main__":
    print("Dynamic Model Selection Module - Self Test")
    print("=" * 50)

    # Test 1: Load default settings
    print("\n1. Testing load_switching_settings()...")
    settings = load_switching_settings()
    print(f"   Loaded: {settings}")

    # Test 2: Save settings
    print("\n2. Testing save_switching_settings()...")
    result = save_switching_settings("Alternative", 70)
    print(f"   Save result: {result}")

    # Test 3: Validate alternate model
    print("\n3. Testing validate_alternate_model_exists()...")
    for mode in ["CHAT_MODE", "ACTION_MODE"]:
        exists = validate_alternate_model_exists(mode)
        print(f"   {mode}: {exists}")

    # Test 4: Get model names
    print("\n4. Testing get_model_name_from_file()...")
    for mode in ["CHAT_MODE", "ACTION_MODE"]:
        last_used = get_model_name_from_file(MODEL_FILES[mode]["last_used"])
        alternate = get_model_name_from_file(MODEL_FILES[mode]["alternate"])
        print(f"   {mode}:")
        print(f"     Last Used: {last_used}")
        print(f"     Alternate: {alternate}")

    print("\n" + "=" * 50)
    print("Self test complete!")
