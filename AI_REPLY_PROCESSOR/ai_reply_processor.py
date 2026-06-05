"""
ai_reply_processor.py - AI Reply Post-Processing Module
========================================================

Portable plugin for any AI agent (coding, browsing, computer use, etc.)

Purpose:
- Apply layered filters to AI replies before feeding to the system
- Single source of truth: AI_LAST_REPLY_PROCESSED.txt
- File-based for multi-agent future architecture

Usage:
    processor = AIReplyProcessor(project_path)
    processor.set_reasoning_mode(True)
    processed = processor.process_reply(raw_ai_reply)
"""

import os
import re
import json
from typing import Optional, List


class AIReplyProcessor:
    """
    Post-processing pipeline for AI replies.

    Flow:
    1. Receive raw AI reply
    2. Save to LAST_AI_FULL_RESPONSE.txt
    3. Apply processing layers (reasoning, emoji filter, etc.)
    4. Save to LAST_AI_PROCESSED_RESPONSE.txt
    5. Read from LAST_AI_PROCESSED_RESPONSE.txt (single source of truth)
    6. Return processed content
    """

    def __init__(self, project_path: str):
        """
        Initialize processor.

        Creates AI_REPLY_PROCESSOR/ folder in project root if it doesn't exist.
        """
        self.project_path = project_path
        self.reply_folder = os.path.join(project_path, "AI_REPLY_PROCESSOR")
        self.config_file = os.path.join(project_path, "AI_REPLY_PROCESSOR", "processor_config.json")

        # Create folder if doesn't exist
        os.makedirs(self.reply_folder, exist_ok=True)

        # File paths
        self.full_reply_file = os.path.join(self.reply_folder, "LAST_AI_FULL_RESPONSE.txt")
        self.processed_reply_file = os.path.join(self.reply_folder, "LAST_AI_PROCESSED_RESPONSE.txt")

        # Processing flags (controlled by commands)
        self.reasoning_mode = False  # Default: disabled
        self.emoji_filter = False    # Future
        self.format_mode = None      # Future

        # Configurable end tags for reasoning model detection
        self.end_tags = ["</think>", "</thinking>"]

        # Load saved configuration
        self._load_config()


    def process_reply(self, raw_reply: str) -> str:
        """
        Main processing pipeline.

        Args:
            raw_reply: Unprocessed AI reply

        Returns:
            Processed reply (read from AI_LAST_REPLY_PROCESSED.txt)

        Raises:
            ValueError: If post-processing produces empty output
        """
        # Handle None or empty input
        if not raw_reply:
            raise ValueError("Raw AI reply is None or empty")

        # Step 1: Save full reply (debugging, audit trail)
        self._save_full_reply(raw_reply)

        # Step 2: Apply processing layers
        processed = raw_reply

        # Layer 1: Reasoning tag removal (if enabled)
        if self.reasoning_mode:
            processed = self._remove_thinking_tags(processed)

        # Layer 2: Emoji filter (if enabled) - FUTURE
        if self.emoji_filter:
            processed = self._remove_emojis(processed)

        # Layer 3: Format processing (if enabled) - FUTURE
        # if self.format_mode:
        #     processed = self._apply_formatting(processed)

        # Step 3: Validate processed reply is not empty
        if not processed or len(processed.strip()) < 10:
            raise ValueError(
                f"Post-processing produced empty or too-short output. "
                f"Original length: {len(raw_reply)}, Processed length: {len(processed.strip())}"
            )

        # Step 4: Save processed reply (SINGLE SOURCE OF TRUTH)
        self._save_processed_reply(processed)

        # Step 5: Read from file and return
        # (Future: multiple agents can access this file)
        return self._read_processed_reply()


    def _remove_thinking_tags(self, text: str) -> str:
        """
        Remove thinking content from reasoning model output.

        Strategy:
        1. Find the LAST occurrence of any configured end tag (e.g. </think>, </thinking>)
        2. Verify it's not inside a code block (false positive check)
        3. Return everything AFTER the last end tag

        No opening tag required — many models (e.g. Qwen 3.5) output thinking
        as plain text without an opening <think> tag.

        Args:
            text: Raw AI reply with potential thinking tags

        Returns:
            Content after the last end tag, or original text if no tag found
        """
        best_pos = -1
        best_match = None

        for tag in self.end_tags:
            close_escaped = re.escape(tag)
            close_matches = list(re.finditer(close_escaped, text, re.IGNORECASE))
            if close_matches:
                last_match = close_matches[-1]
                pos = last_match.end()
                if pos > best_pos:
                    best_pos = pos
                    best_match = last_match

        # No end tag found - return original text (graceful fallback)
        if best_match is None:
            return text

        # Verify not in code block (false positive check)
        code_block_pattern = r'```.*?```'
        code_blocks = list(re.finditer(code_block_pattern, text, re.DOTALL))

        in_code_block = any(
            block.start() <= best_match.start() <= block.end()
            for block in code_blocks
        )

        if in_code_block:
            return text

        # Extract content after the last end tag
        content_after = text[best_pos:].strip()

        # If no substantial content after tag, return original (incomplete response)
        if len(content_after) < 5:
            return text

        return content_after


    def _remove_emojis(self, text: str) -> str:
        """
        Remove emojis from text (FUTURE FUNCTION).

        Args:
            text: Input text with potential emojis

        Returns:
            Text with emojis removed
        """
        # Placeholder for future implementation
        # Could use emoji library or regex patterns
        return text


    def _save_full_reply(self, reply: str):
        """Save full unmodified AI reply to file."""
        try:
            with open(self.full_reply_file, 'w', encoding='utf-8') as f:
                f.write(reply)
        except Exception as e:
            # Non-critical error - log but don't fail
            print(f"⚠️  Warning: Could not save full reply to file: {e}")


    def _save_processed_reply(self, reply: str):
        """Save processed reply to file (SINGLE SOURCE OF TRUTH)."""
        try:
            with open(self.processed_reply_file, 'w', encoding='utf-8') as f:
                f.write(reply)
        except Exception as e:
            # Critical error - this is the source of truth
            raise IOError(f"Failed to save processed reply: {e}")


    def _read_processed_reply(self) -> str:
        """
        Read processed reply from file (SINGLE SOURCE OF TRUTH).

        This is the definitive output used by:
        - The coding agent
        - RAG memory storage
        - Any other agents (future)

        Returns:
            Processed reply content
        """
        try:
            with open(self.processed_reply_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Failed to read processed reply: {e}")


    # ============================================================
    # CONFIGURATION PERSISTENCE
    # ============================================================

    def _load_config(self):
        """Load reasoning mode and end tags from config file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.reasoning_mode = config.get('reasoning_mode', False)
                    self.end_tags = config.get('end_tags', ["</think>", "</thinking>"])
                    if self.reasoning_mode:
                        print(f"✅ Reasoning mode loaded from config: ENABLED (end_tags: {self.end_tags})")
        except Exception as e:
            # Silently fail - not critical
            pass

    def _save_config(self):
        """Save reasoning mode and end tags to config file."""
        try:
            # Load existing config or create new one
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

            # Update settings
            config['reasoning_mode'] = self.reasoning_mode
            config['end_tags'] = self.end_tags

            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save reasoning config: {e}")

    # ============================================================
    # COMMAND HANDLERS (for /reasoning, etc.)
    # ============================================================

    def set_reasoning_mode(self, enabled: bool):
        """Enable or disable reasoning mode and persist to config."""
        self.reasoning_mode = enabled
        self._save_config()  # Persist the setting

    def set_end_tags(self, tags_list: List[str]):
        """Set configurable end tags for reasoning model detection and persist to config."""
        if tags_list:
            self.end_tags = tags_list
        self._save_config()

    def find_end_tag_position(self, accumulated_text: str) -> int:
        """
        Find the position AFTER the last end tag in accumulated text.
        Used during streaming to detect when thinking phase ends.

        Args:
            accumulated_text: The full accumulated response so far

        Returns:
            Position after the last end tag (start of real content), or -1 if not found.
        """
        best_pos = -1
        for tag in self.end_tags:
            # Case-insensitive search for the tag
            lower_text = accumulated_text.lower()
            lower_tag = tag.lower()
            idx = lower_text.rfind(lower_tag)
            if idx >= 0:
                pos = idx + len(tag)
                if pos > best_pos:
                    best_pos = pos
        return best_pos

    def set_emoji_filter(self, enabled: bool):
        """Enable or disable emoji filter (FUTURE)."""
        self.emoji_filter = enabled


    def get_status(self) -> dict:
        """
        Get current processing flags for debugging.

        Returns:
            Dictionary with current settings
        """
        return {
            "reasoning_mode": self.reasoning_mode,
            "end_tags": self.end_tags,
            "emoji_filter": self.emoji_filter,
            "full_reply_file": self.full_reply_file,
            "processed_reply_file": self.processed_reply_file,
            "reply_folder": self.reply_folder
        }
