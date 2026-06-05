"""
Vision RAG Helper Functions
============================

Helper functions for integrating Vision RAG into the main application.
Handles user prompt extraction, tagging, and proper memory storage.
"""

import re
from typing import Optional, Tuple
from PIL import Image


def extract_user_prompt_from_full_prompt(full_prompt: str) -> str:
    """
    Extract the actual user prompt from full prompt (which may contain system prompt,
    context memory, and RAG context).

    Scans in reverse order to find the LAST occurrence of:
    - "User Mobile(timestamp):"
    - "User Desktop(timestamp):"
    - "User Robot(timestamp):"

    Returns everything AFTER that marker as the clean user prompt.

    Args:
        full_prompt: The complete prompt sent to LLM (system + context + RAG + user)

    Returns:
        Clean user prompt (just what the user typed)

    Example:
        full_prompt = "System: You are...\n\nContext: ...\n\nUser Desktop(2025-12-24 22:00:00): Hello AI"
        Returns: "Hello AI"
    """
    user_patterns = [
        r"User Mobile \(([^)]+)\): (.*?)(?=\n\s*(?:User|AI Agent)|$)",
        r"User Desktop\(([^)]+)\): (.*?)(?=\n\s*(?:User|AI Agent)|$)",
        r"User Robot\(([^)]+)\): (.*?)(?=\n\s*(?:User|AI Agent)|$)"
    ]

    most_recent_input = ""
    latest_timestamp = ""

    for pattern in user_patterns:
        matches = re.findall(pattern, full_prompt, re.DOTALL)
        for timestamp, message in matches:
            if timestamp > latest_timestamp:
                latest_timestamp = timestamp
                most_recent_input = message.strip()

    # Fallback: if no pattern found, try simple extraction
    if not most_recent_input:
        # Look for the last line that looks like user input
        lines = full_prompt.strip().split('\n')
        for line in reversed(lines):
            if line.strip() and not line.startswith('===') and not line.startswith('System'):
                # Remove any leading "User Desktop:" etc if present
                cleaned = re.sub(r'^User (Mobile|Desktop|Robot)\([^)]+\):\s*', '', line)
                if cleaned.strip():
                    most_recent_input = cleaned.strip()
                    break

    return most_recent_input


def determine_vision_memory_tag(user_attached_image: bool, is_ai_response: bool,
                                is_automated: bool) -> str:
    """
    Determine the appropriate tag for Vision RAG storage.

    Tagging Strategy:
    - User chatting (not automated):
      - Text-only prompt → "[USER_FACE] User instructed vision memory"
      - With attached image → "[USER_ATTACHED_IMAGE] User instructed vision memory"
      - AI response → "[AI_FACE] User instructed vision memory"

    - Automated (screen recording, scheduled agents):
      - All → "[AUTO_SCREENSHOT] Auto generated vision memory"

    Args:
        user_attached_image: True if user sent an image
        is_ai_response: True if this is AI's response
        is_automated: True if this is automated (not direct user chat)

    Returns:
        Appropriate tag string
    """
    if is_automated:
        # Automated processes (screen recording, scheduled agents, etc.)
        return "[AUTO_SCREENSHOT] Auto generated vision memory"
    else:
        # User-involved chatting
        if is_ai_response:
            return "[AI_FACE] User instructed vision memory"
        elif user_attached_image:
            return "[USER_ATTACHED_IMAGE] User instructed vision memory"
        else:
            return "[USER_FACE] User instructed vision memory"


def should_use_gates_for_vision_memory(tag: str) -> bool:
    """
    Determine if storage gates should be used based on memory tag.

    Gates Logic:
    - "User instructed vision memory" → NO gates (store everything, supervised learning)
    - "Auto generated vision memory" → YES gates (filter redundant screenshots)

    Args:
        tag: Vision memory tag string

    Returns:
        True if gates should be used, False to bypass gates
    """
    if "Auto generated" in tag:
        return True  # Use gates for automated memories
    else:
        return False  # Bypass gates for user-instructed memories


def get_identity_image(tag: str) -> Tuple[Optional[Image.Image], str]:
    """
    Get the appropriate identity image based on tag.

    Args:
        tag: Vision memory tag

    Returns:
        Tuple of (PIL Image or None, image_path)
        Returns (None, "") for USER_ATTACHED_IMAGE (use actual attached image)
    """
    if "[USER_FACE]" in tag:
        path = "Vision_RAG/Identity_Faces/USER.jpg"
        try:
            img = Image.open(path)
            return img, path
        except Exception as e:
            print(f"⚠️  Could not load USER face from {path}: {e}")
            return None, ""

    elif "[AI_FACE]" in tag:
        path = "Vision_RAG/Identity_Faces/AI.png"
        try:
            img = Image.open(path)
            return img, path
        except Exception as e:
            print(f"⚠️  Could not load AI face from {path}: {e}")
            return None, ""

    elif "[USER_ATTACHED_IMAGE]" in tag:
        # User attached image - caller should provide the actual image
        return None, ""

    elif "[AUTO_SCREENSHOT]" in tag:
        # Screenshot - caller should provide the actual screenshot
        return None, ""

    else:
        print(f"⚠️  Unknown tag: {tag}")
        return None, ""


# Example usage for integration:
"""
# In CHAT_MODE response flow (Desktop/Android, Streaming/Non-Streaming):

# 1. Extract user prompt from full prompt
user_prompt = extract_user_prompt_from_full_prompt(full_prompt)

# 2. Determine tag
if user_attached_image:
    tag = determine_vision_memory_tag(user_attached_image=True, is_ai_response=False, is_automated=False)
    image_to_store = user_image  # Actual attached image
else:
    tag = determine_vision_memory_tag(user_attached_image=False, is_ai_response=False, is_automated=False)
    image_to_store, _ = get_identity_image(tag)  # USER.jpg

# 3. Store user vision memory
if image_to_store:
    context_text = f"{tag} User: {user_prompt}"
    use_gates = should_use_gates_for_vision_memory(tag)

    memory_id = update_vision_rag_memories(
        image=image_to_store,
        context_text=context_text,
        outcome=None,
        mode="USER_CHAT" if not use_gates else "AUTO_PROCESS"
    )

# 4. Store AI response vision memory
ai_tag = determine_vision_memory_tag(user_attached_image=False, is_ai_response=True, is_automated=False)
ai_image, _ = get_identity_image(ai_tag)
if ai_image:
    context_text = f"{ai_tag} AI: {ai_response}"
    use_gates = should_use_gates_for_vision_memory(ai_tag)

    memory_id = update_vision_rag_memories(
        image=ai_image,
        context_text=context_text,
        outcome=None,
        mode="USER_CHAT" if not use_gates else "AUTO_PROCESS"
    )

# 5. Display stats (like TEXT RAG)
stats = get_vision_memory_stats()
print(f"✅ [VISION RAG] Memory stats after update: {stats}")
"""
