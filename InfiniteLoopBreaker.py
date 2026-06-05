"""
InfiniteLoopBreaker.py

This module provides classes for detecting and breaking infinite loops in browser automation.
It implements three main strategies:
1. State tracking to detect repetitive states
2. Tab-based progress management for maintaining checkpoints
3. Progress tracking to detect stalled tasks

The classes work together but can also be used independently for gradual integration.
"""

import logging
import hashlib
import time
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import asyncio
import json
from typing import TypedDict, Optional
import re
###Linux Change 1 Start####
from platform_utils import get_platform
import os
###Linux Change 1 End####

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DOMUtils:
    """Shared utilities for DOM manipulation"""

    @staticmethod
    def extract_visible_text(element_tree: Any) -> str:
        """Extracts visible text content from the DOM tree"""
        if not element_tree:
            return ""

        text_content = []
        if hasattr(element_tree, 'text') and element_tree.text:
            text_content.append(element_tree.text)

        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                text_content.append(DOMUtils.extract_visible_text(child))

        return " ".join(text_content)

    @staticmethod
    def get_interactive_elements_count(element_tree: Any) -> int:
        """Counts interactive elements in the DOM tree"""
        if not element_tree:
            return 0

        count = 0
        if hasattr(element_tree, 'tag_name'):
            if element_tree.tag_name in ['button', 'a', 'input', 'select', 'textarea']:
                count += 1

        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                count += DOMUtils.get_interactive_elements_count(child)

        return count

    @staticmethod
    def count_dom_nodes(element_tree: Any) -> int:
        """
        Recursively counts the number of nodes in a DOM tree.

        Args:
            element_tree: The root node of the DOM tree

        Returns:
            int: Total number of nodes in the tree
        """
        if not element_tree:
            return 0

        count = 1  # Count current node

        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                count += DOMUtils.count_dom_nodes(child)

        return count

    @staticmethod
    def get_dynamic_content_state(element_tree: Any) -> str:
        """
        Analyzes dynamic content like lists, tables, and scrollable areas.
        Helps distinguish between actual loops and normal dynamic content behavior.

        Args:
            element_tree: The DOM tree to analyze

        Returns:
            str: A string representation of the dynamic content state
        """
        if not element_tree:
            return "empty"

        # Track visible items and their properties
        visible_items = []
        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                if hasattr(child, 'is_visible') and child.is_visible:
                    item_info = {
                        'tag': getattr(child, 'tag_name', 'unknown'),
                        'position': getattr(child, 'highlight_index', -1),
                        'interactive': child.tag_name in ['button', 'a', 'input', 'select', 'textarea']
                    }
                    visible_items.append(item_info)

        # Create a state signature for dynamic content
        dynamic_state = {
            'visible_count': len(visible_items),
            'interactive_positions': [i['position'] for i in visible_items if i['interactive']],
            'content_type': 'list' if any(i['tag'] in ['li', 'tr', 'div'] for i in visible_items) else 'general'
        }

        return f"dynamic:{json.dumps(dynamic_state)}"


###NEW: DOM Refresh Monitor for detecting stuck states###
class DOMRefreshMonitor:
    """
    Monitors DOM state changes and triggers recovery when stuck.
    PRIMARY RECOVERY STRATEGY: New tab + close previous tab
    """

    def __init__(self, timeout_seconds: int = 60):
        self.timeout = timeout_seconds
        self.last_dom_change_time = time.time()
        self.last_dom_hash = None
        self.recovery_attempt_count = 0
        self.recovery_history = []
        logger.info(f"🔍 DOMRefreshMonitor initialized with {timeout_seconds}s timeout")

    def check_dom_changed(self, current_state: Any) -> bool:
        """
        Check if DOM has changed since last check.
        Returns True if DOM changed (resets timer), False otherwise.
        """
        # FIX 2026-01-17: Detect minimal/fallback state (DOM retrieval failed)
        # When DOM retrieval fails, we get empty element_tree - don't trigger timeout for this
        is_minimal_state = False
        if hasattr(current_state, 'element_tree') and current_state.element_tree:
            # Check if this is a minimal/fallback state (empty children = DOM retrieval failed)
            if hasattr(current_state.element_tree, 'children'):
                is_minimal_state = len(current_state.element_tree.children) == 0

        if is_minimal_state:
            # DOM retrieval failed - reset timer but don't count as "change"
            # This prevents false timeout triggers when page is in SPA transition
            self.last_dom_change_time = time.time()
            logger.info("🔄 DOM retrieval returned minimal state (SPA transition) - timer reset")
            return False  # Return False so we don't reset recovery_attempt_count

        current_hash = self._compute_dom_hash(current_state)

        if current_hash != self.last_dom_hash:
            # DOM changed - reset timer
            self.last_dom_hash = current_hash
            self.last_dom_change_time = time.time()
            self.recovery_attempt_count = 0  # Reset recovery count on successful change
            logger.debug(f"✅ DOM changed detected, timer reset (hash: {current_hash[:8]}...)")
            return True

        logger.debug(f"⏸️  No DOM change detected (hash still: {current_hash[:8]}...)")
        return False

    def is_timeout_exceeded(self) -> bool:
        """Check if DOM hasn't changed for timeout duration"""
        elapsed = time.time() - self.last_dom_change_time
        exceeded = elapsed >= self.timeout

        if exceeded:
            logger.warning(
                f"⚠️ DOM TIMEOUT EXCEEDED! No changes for {elapsed:.1f}s "
                f"(limit: {self.timeout}s, attempt: {self.recovery_attempt_count + 1})"
            )

        return exceeded

    def get_time_until_timeout(self) -> int:
        """Get remaining seconds until timeout"""
        elapsed = time.time() - self.last_dom_change_time
        remaining = self.timeout - elapsed
        return max(0, int(remaining))

    def get_recovery_action(self) -> str:
        """
        Get next recovery action based on attempt count.

        Recovery Strategy (Escalating):
        1st timeout: NEW_TAB (primary - keeps memory intact)
        2nd timeout: SCROLL_AND_WAIT (maybe lazy loading)
        3rd timeout: REFRESH_PAGE (force reload)
        4th timeout: GO_BACK (navigation issue)
        5th+ timeout: STOP_TASK (unrecoverable)
        """
        self.recovery_attempt_count += 1

        if self.recovery_attempt_count == 1:
            action = "NEW_TAB"
        elif self.recovery_attempt_count == 2:
            action = "SCROLL_AND_WAIT"
        elif self.recovery_attempt_count == 3:
            action = "REFRESH_PAGE"
        elif self.recovery_attempt_count == 4:
            action = "GO_BACK"
        else:
            action = "STOP_TASK"

        logger.warning(
            f"🚨 DOM Recovery Action #{self.recovery_attempt_count}: {action}"
        )

        # Track recovery in history
        self.recovery_history.append({
            "attempt": self.recovery_attempt_count,
            "action": action,
            "timestamp": time.time()
        })

        return action

    def _compute_dom_hash(self, state: Any) -> str:
        """Compute hash of DOM state for change detection"""
        if not state:
            return "empty_state"

        # Use DOMUtils to extract relevant state information
        try:
            if hasattr(state, 'element_tree'):
                visible_text = DOMUtils.extract_visible_text(state.element_tree)[:1000]
                interactive_count = DOMUtils.get_interactive_elements_count(state.element_tree)
                node_count = DOMUtils.count_dom_nodes(state.element_tree)

                # Combine URL, text, and structure info for hash
                url = getattr(state, 'url', 'no_url')
                hash_input = f"{url}|{visible_text}|{interactive_count}|{node_count}"
            else:
                # Fallback if element_tree not available
                hash_input = str(state)

            computed_hash = hashlib.md5(hash_input.encode()).hexdigest()
            return computed_hash

        except Exception as e:
            logger.error(f"❌ Error computing DOM hash: {e}")
            return "error_state"


###Class for alternative action methods
class ActionAlternatives:
    """
    Provides alternative methods for common browser actions.
    Helps break out of loops by suggesting different interaction approaches.
    """

    @staticmethod
    def get_click_alternatives(element_tree: Any) -> List[Dict[str, str]]:
        """
        Suggests alternative clicking methods based on element type.

        Args:
            element_tree: The element to analyze

        Returns:
            List of dictionaries containing method name and description
        """
        base_alternatives = [
            {"method": "standard_click", "description": "Regular Playwright click"},
            {"method": "force_click", "description": "Force click ignoring overlay elements"},
            {"method": "javascript_click", "description": "Direct JavaScript click event"},
            {"method": "keyboard_enter", "description": "Focus and press Enter"}
        ]

        if hasattr(element_tree, 'tag_name'):
            if element_tree.tag_name == 'input':
                base_alternatives.extend([
                    {"method": "focus_then_click", "description": "Focus first, then click"},
                    {"method": "tab_to_element", "description": "Tab navigation to element"}
                ])
            elif element_tree.tag_name == 'a':
                base_alternatives.extend([
                    {"method": "href_navigation", "description": "Direct URL navigation"},
                    {"method": "new_tab_open", "description": "Open in new tab"}
                ])

        return base_alternatives

    @staticmethod
    def get_scroll_alternatives() -> List[Dict[str, str]]:
        """Provides alternative scrolling methods"""
        return [
            {"method": "smooth_scroll", "description": "Smooth scrolling to element"},
            {"method": "jump_scroll", "description": "Immediate scroll to position"},
            {"method": "scroll_into_view", "description": "Element scrollIntoView"},
            {"method": "keyboard_scroll", "description": "Page Down key scroll"},
            {"method": "incremental_scroll", "description": "Small step scrolling"}
        ]

    @staticmethod
    def get_selection_alternatives() -> List[Dict[str, str]]:
        """Provides alternative element selection methods"""
        return [
            {"method": "direct_selection", "description": "Direct element selector"},
            {"method": "relative_selection", "description": "Selection by relative position"},
            {"method": "text_match", "description": "Selection by visible text"},
            {"method": "parent_child", "description": "Navigate through parent"},
            {"method": "xpath_selection", "description": "XPath-based selection"}
        ]


@dataclass
class TabState:
    """
    Stores the state information for a browser tab.
    Used by TabBasedProgressManager to track tab history and progress.
    """
    tab_id: int
    url: str
    title: str
    step_count: int
    last_action_time: float
    state_fingerprint: str
    progress_score: float = 0.0
    successful_actions: int = 0
    failed_actions: int = 0

# First, define the structure of our state data
class StateData(TypedDict):
    url: str
    title: str
    tab_id: Optional[int]
    content_hash: str
    interactive_elements: int
    is_loading: bool
    page_ready: bool
    dynamic_content_stable: bool
    last_update_time: float

class StateTracker:
    """
    Enhanced state tracking system that maintains synchronization between browser state,
    AI actions, and memory updates. Provides verified state transitions and loop detection
    with tab awareness.
    """

    def __init__(self, max_similar_states: int = 3, state_timeout: int = 120):  ####IMPORTANT:::changed state_timeout from 300 to 120 means now it will wait maximum 2 minutes for a page to load. Or else it will open a new tab and close the current tab
        # Core state tracking collections
        self.state_history: List[Tuple[str, Optional[int]]] = []
        self.last_unique_states: List[Tuple[float, str, Optional[int]]] = []

        # Configuration parameters
        self.max_similar_states = max_similar_states
        self.state_timeout = state_timeout

        # State verification tracking
        self.last_confirmed_state: Optional[Dict[str, Any]] = None
        self.last_action_time: float = time.time()

    def _extract_state_data(self, state: Any) -> StateData:  # Change return type to StateData
        """
        Extracts comprehensive state information for accurate state tracking and verification.
        Includes enhanced detection of loading states, dynamic content, and page readiness.
        """
        state_data = {
            'url': getattr(state, 'url', ''),
            'title': getattr(state, 'title', ''),
            'tab_id': None,
            'content_hash': '',
            'interactive_elements': 0,
            'is_loading': False,
            'page_ready': False,
            'dynamic_content_stable': False,
            'last_update_time': time.time()
        }

        if hasattr(state, 'element_tree'):
            # Extract and process visible text
            visible_text = DOMUtils.extract_visible_text(state.element_tree)[:1000]
            state_data['content_hash'] = hashlib.sha256(visible_text.encode()).hexdigest()

            # Count interactive elements
            state_data['interactive_elements'] = DOMUtils.get_interactive_elements_count(state.element_tree)

            # Check for loading indicators
            loading_indicators = [
                'loading',
                'please wait',
                'connecting',
                'processing',
                'updating',
                'refreshing',
                'fetching',
                'spinning',
                'progress'
            ]
            visible_text_lower = visible_text.lower()
            state_data['is_loading'] = any(indicator in visible_text_lower for indicator in loading_indicators)

            # Assess page readiness
            has_content = len(visible_text.strip()) > 0
            has_interactables = state_data['interactive_elements'] > 0
            state_data['page_ready'] = has_content and has_interactables and not state_data['is_loading']

            # Check dynamic content stability
            if hasattr(state, 'cached_state') and hasattr(state.cached_state, 'element_tree'):
                previous_content = DOMUtils.extract_visible_text(state.cached_state.element_tree)[:1000]
                previous_hash = hashlib.sha256(previous_content.encode()).hexdigest()
                content_changed = previous_hash != state_data['content_hash']
                time_since_change = time.time() - getattr(state, 'last_content_change', 0)
                state_data['dynamic_content_stable'] = not content_changed or time_since_change > 1.0
            else:
                state_data['dynamic_content_stable'] = True

        # Enhanced tab tracking
        if hasattr(state, 'tabs'):
            current_url = state_data['url']
            for idx, tab in enumerate(state.tabs):
                tab_url = getattr(tab, 'url', '')
                # More flexible URL matching for dynamic pages
                if tab_url and (tab_url == current_url or
                                current_url.startswith(tab_url) or
                                tab_url.startswith(current_url)):
                    state_data['tab_id'] = idx
                    break

            # If no exact match found but we have tabs, take best guess
            if state_data['tab_id'] is None and len(state.tabs) > 0:
                state_data['tab_id'] = len(state.tabs) - 1  # Assume most recent tab

        return state_data

    def get_state_fingerprint(self, state: Any) -> str:
        """Creates a unique fingerprint of the current DOM state."""
        state_data = self._extract_state_data(state)

        components = [
            f"url:{state_data['url']}",
            f"title:{state_data['title']}",
            f"tab:{state_data['tab_id']}",
            f"content:{state_data['content_hash']}",
            f"interactive:{state_data['interactive_elements']}"
        ]

        if hasattr(state, 'element_tree'):
            dynamic_state = DOMUtils.get_dynamic_content_state(state.element_tree)
            components.append(f"dynamic:{dynamic_state}")

        return hashlib.sha256("||".join(components).encode()).hexdigest()

    def add_state(self, state: Any) -> None:
        """
        Adds a new state to the history with enhanced tab context awareness.
        This method maintains backward compatibility while incorporating
        improved state tracking.
        """
        state_data = self._extract_state_data(state)
        fingerprint = self.get_state_fingerprint(state)
        current_time = time.time()

        # Update last confirmed state
        self.last_confirmed_state = state_data
        self.last_action_time = current_time

        # Add to history with tab context
        self.state_history.append((fingerprint, state_data['tab_id']))
        self.last_unique_states.append((current_time, fingerprint, state_data['tab_id']))

        # Maintain history size
        if len(self.state_history) > 50:
            self.state_history = self.state_history[-50:]

    def is_stuck_in_loop(self, current_state: Any) -> Tuple[bool, str]:
        """
        Enhanced loop detection with verified state tracking and tab awareness.
        """
        current_data = self._extract_state_data(current_state)
        current_fingerprint = self.get_state_fingerprint(current_state)
        current_time = time.time()

        # Clean up old states
        self.last_unique_states = [
            (t, f, tab_id) for t, f, tab_id in self.last_unique_states
            if current_time - t <= self.state_timeout
        ]

        # Count similar states within same tab context
        similar_states = sum(
            1 for _, fingerprint, tab_id in self.last_unique_states[-10:]
            if fingerprint == current_fingerprint and tab_id == current_data['tab_id']
        )

        # Add current state
        self.last_unique_states.append((current_time, current_fingerprint, current_data['tab_id']))

        # Check loop conditions with context
        if similar_states >= self.max_similar_states:
            return True, f"Multiple similar states detected in tab {current_data['tab_id']}"

        # Check for timeout-based stalling
        if len(self.last_unique_states) > 1:
            same_tab_states = [
                (t, f) for t, f, tab in self.last_unique_states
                if tab == current_data['tab_id']
            ]
            if same_tab_states:
                oldest_time = same_tab_states[-min(5, len(same_tab_states))][0]
                if current_time - oldest_time > self.state_timeout:
                    return True, f"State timeout exceeded in tab {current_data['tab_id']}"

        return False, ""

    def suggest_alternative_action(self, current_state: Any) -> Tuple[str, List[Dict[str, str]]]:
        """
        Suggests alternative actions based on verified state analysis.
        """
        current_data = self._extract_state_data(current_state)

        if not hasattr(current_state, 'element_tree'):
            return "Page may be loading", [{"method": "refresh", "description": "Refresh the page"}]

        content_text = DOMUtils.extract_visible_text(current_state.element_tree).lower()
        recent_fingerprints = [f for _, f, _ in self.last_unique_states[-5:]]

        # Analyze patterns for targeted alternatives
        if "click" in str(recent_fingerprints):
            return (
                f"Click action may be failing in tab {current_data['tab_id']}",
                ActionAlternatives.get_click_alternatives(current_state.element_tree)
            )
        elif "scroll" in content_text or "list" in content_text:
            return (
                "Content may be dynamically loading",
                ActionAlternatives.get_scroll_alternatives()
            )
        elif "select" in content_text or "choose" in content_text:
            return (
                "Selection method may need adjustment",
                ActionAlternatives.get_selection_alternatives()
            )

        return (
            "Consider alternative navigation approach",
            ActionAlternatives.get_click_alternatives(current_state.element_tree)
        )


class TabBasedProgressManager:
    """
    Manages browser tabs for progress tracking and recovery.
    Implements checkpoint system using browser tabs.
    """

    def __init__(self, browser_context: Any, steps_per_tab: int = 5, max_tabs: int = 3):
        self.browser_context = browser_context
        self.steps_per_tab = steps_per_tab
        self.max_tabs = max_tabs
        self.tab_states: Dict[int, TabState] = {}
        self.current_tab_id: Optional[int] = None
        self.state_tracker = StateTracker()

    async def initialize_tab(self, tab_id: int, state: Any) -> None:
        """
        Initializes a new tab with its initial state.

        Args:
            tab_id: Unique identifier for the tab
            state: Initial browser state
        """
        self.tab_states[tab_id] = TabState(
            tab_id=tab_id,
            url=state.url,
            title=state.title,
            step_count=0,
            last_action_time=time.time(),
            state_fingerprint=self.state_tracker.get_state_fingerprint(state)
        )
        self.current_tab_id = tab_id
        logger.info(f"Initialized new tab {tab_id} at URL: {state.url}")

    async def manage_tabs(self, current_step: int, current_state: Any) -> None:
        """
        Manages tab creation, switching, and cleanup based on progress.

        Args:
            current_step: Current step number in the task
            current_state: Current browser state
        """
        if not self.current_tab_id:
            await self.initialize_tab(0, current_state)
            return

        current_tab = self.tab_states[self.current_tab_id]
        current_tab.step_count += 1

        # Check if we need a new tab
        if current_tab.step_count >= self.steps_per_tab:
            await self._create_new_tab(current_state)

        # Update state tracking
        self.state_tracker.add_state(current_state)

        # Check for stuck states
        is_stuck, reason = self.state_tracker.is_stuck_in_loop(current_state)
        if is_stuck:
            logger.warning(f"Detected stuck state: {reason}")
            await self._handle_stuck_state()

    async def _create_new_tab(self, current_state: Any) -> None:
        """
        Creates a new tab and manages tab history.

        Args:
            current_state: Current browser state
        """
        new_tab_id = max(self.tab_states.keys()) + 1 if self.tab_states else 0

        try:
            await self.browser_context.create_new_tab()
            await self.initialize_tab(new_tab_id, current_state)

            # Manage tab limit
            if len(self.tab_states) > self.max_tabs:
                oldest_tab_id = min(self.tab_states.keys())
                await self.browser_context.close_tab(oldest_tab_id)
                del self.tab_states[oldest_tab_id]
                logger.info(f"Closed oldest tab {oldest_tab_id} to maintain tab limit")

        except Exception as e:
            logger.error(f"Error creating new tab: {str(e)}")
            raise

    async def _handle_stuck_state(self) -> None:
        """
        Handles recovery when stuck in a loop.
        Reverts to previous tab and cleans up stuck state.
        """
        if len(self.tab_states) <= 1:
            logger.warning("Stuck in loop but no previous tab available for recovery")
            return

        current_tab_id = self.current_tab_id
        previous_tab_id = max(tab_id for tab_id in self.tab_states.keys()
                              if tab_id < current_tab_id)

        try:
            # Switch to previous tab
            await self.browser_context.switch_to_tab(previous_tab_id)
            await self.browser_context.close_tab(current_tab_id)

            # Update tracking
            del self.tab_states[current_tab_id]
            self.current_tab_id = previous_tab_id

            logger.info(f"Successfully reverted to previous tab {previous_tab_id}")

        except Exception as e:
            logger.error(f"Error during stuck state recovery: {str(e)}")
            raise

class ProgressTracker:
    """
    Tracks overall task progress and detects stalled states.
    Uses multiple indicators to measure task completion progress.
    """

    def __init__(self, task_description: str):
        self.task_description = task_description
        self.progress_history: List[float] = []
        self.last_progress_time = time.time()
        self.progress_timeout = 300  # 5 minutes
        self.success_indicators: List[str] = []
        self._initialize_success_indicators()

    def _initialize_success_indicators(self) -> None:
        """
        Initializes success indicators based on task description.
        Extracts key terms and expected outcomes from the task.
        """
        # Extract key verbs and nouns from task description
        words = self.task_description.lower().split()
        self.success_indicators = [word for word in words
                                   if len(word) > 3 and not word.isspace()]

    def update_progress(self, current_state: Any) -> float:
        """
        Calculates and updates progress score based on current state.

        Args:
            current_state: Current browser state

        Returns:
            float: Current progress score (0.0 to 1.0)
        """
        progress_score = self._calculate_progress_score(current_state)

        self.progress_history.append(progress_score)
        self.last_progress_time = time.time()

        # Keep history manageable
        if len(self.progress_history) > 50:
            self.progress_history = self.progress_history[-50:]

        return progress_score

    def _calculate_progress_score(self, current_state: Any) -> float:
        """
        Calculates a progress score based on state and success indicators.

        Args:
            current_state: Current browser state

        Returns:
            float: Progress score between 0.0 and 1.0
        """
        score = 0.0

        if hasattr(current_state, 'element_tree'):
            content = DOMUtils.extract_visible_text(current_state.element_tree)

            # Check for success indicators in content
            for indicator in self.success_indicators:
                if indicator in content.lower():
                    score += 0.2

            # Consider page structure and interactive elements
            interactive_elements = DOMUtils.get_interactive_elements_count(current_state.element_tree)
            if interactive_elements > 0:
                score += 0.1  # Small bonus for having interactive elements

        return min(score, 1.0)

    def is_progress_stalled(self) -> Tuple[bool, str]:
        """
        Determines if progress has stalled based on timeout and score history.

        Returns:
            Tuple[bool, str]: (is_stalled, reason)
        """
        current_time = time.time()

        # Check timeout
        if current_time - self.last_progress_time > self.progress_timeout:
            return True, "Progress timeout exceeded"

        # Check progress trend
        if len(self.progress_history) >= 5:
            recent_progress = self.progress_history[-5:]
            if max(recent_progress) - min(recent_progress) < 0.1:
                return True, "No significant progress in recent steps"

        return False, ""

##########Separate class file for content extraction fallback
class ContentExtractionFallback:
    """
    Provides fallback methods for content extraction when the primary method fails.
    Uses multiple strategies with progressive fallbacks without page-specific logic.
    """

    @staticmethod
    async def extract_with_fallbacks(browser_context, max_attempts=3):
        """
        Attempts to extract content using multiple fallback methods.

        Args:
            browser_context: The browser context to use
            max_attempts: Maximum number of fallback strategies to try

        Returns:
            str: Extracted content or error message
        """
        if not browser_context:
            return "No browser context available"

        strategies = [
            ContentExtractionFallback._extract_via_dom,
            ContentExtractionFallback._extract_via_javascript,
            ContentExtractionFallback._extract_via_frames,
            ContentExtractionFallback._extract_via_visible_text
        ]

        results = []
        page = await browser_context.get_current_page()

        for i, strategy in enumerate(strategies[:max_attempts]):
            try:
                content = await strategy(page)
                if content and len(content.strip()) > 50:  # Only accept non-trivial content
                    results.append(content)
                    if len(content) > 200:  # If we got substantial content, we can stop
                        break
            except Exception as e:
                logging.debug(f"Extraction strategy {i + 1} failed: {str(e)}")
                continue

        # Combine results or return the best one
        if results:
            if len(results) == 1:
                return results[0]
            else:
                # Return the longest result as it's likely the most complete
                return max(results, key=len)

        return "Could not extract content after multiple attempts."

    @staticmethod
    async def _extract_via_dom(page):
        """Extract content via standard DOM methods"""
        # Get text from common content containers
        selectors = [
            'main', 'article', '.content', '#content',
            '[role="main"]', '.main-content',
            '.body', '.message-body', '.post-content'
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text and len(text.strip()) > 50:
                        return text.strip()
            except:
                continue

        # Fallback to body content
        body = await page.query_selector('body')
        if body:
            return await body.text_content()

        return ""

    @staticmethod
    async def _extract_via_javascript(page):
        """Extract content using JavaScript execution"""
        return await page.evaluate('''() => {
            // Try to identify the main content area
            const contentSelectors = [
                // By role
                '[role="main"]', '[role="article"]', '[role="contentinfo"]',
                // By common IDs
                '#main', '#content', '#main-content', '#article',
                // By common classes
                '.content', '.main', '.article', '.post', '.message'
            ];

            // Try each selector
            for (const selector of contentSelectors) {
                const element = document.querySelector(selector);
                if (element && element.textContent.trim().length > 50) {
                    return element.textContent;
                }
            }

            // If no main content area found, get all visible paragraphs
            const paragraphs = Array.from(document.querySelectorAll('p, h1, h2, h3, li, td, div > text'))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' &&
                           el.textContent.trim().length > 0;
                })
                .map(el => el.textContent.trim())
                .join('\\n\\n');

            return paragraphs || document.body.textContent;
        }''')

    @staticmethod
    async def _extract_via_frames(page):
        """Extract content from frames and iframes"""
        # Try to get content from frames (often used in email clients, rich editors)
        return await page.evaluate('''() => {
            const frameContents = [];

            // Get all iframes
            const frames = document.querySelectorAll('iframe');
            for (const frame of frames) {
                try {
                    const doc = frame.contentDocument || frame.contentWindow.document;
                    if (doc && doc.body) {
                        frameContents.push(doc.body.textContent);
                    }
                } catch(e) {
                    // Cross-origin frame access will fail, skip these
                }
            }

            return frameContents.join('\\n\\n');
        }''')

    @staticmethod
    async def _extract_via_visible_text(page):
        """Last resort: extract all visible text elements"""
        return await page.evaluate('''() => {
            // Get all text nodes that are visible
            const textNodes = [];
            const walk = document.createTreeWalker(
                document.body, 
                NodeFilter.SHOW_TEXT, 
                null, 
                false
            );

            while(node = walk.nextNode()) {
                const parentStyle = window.getComputedStyle(node.parentElement);
                if (parentStyle.display !== 'none' && 
                    parentStyle.visibility !== 'hidden' && 
                    node.textContent.trim().length > 0) {
                    textNodes.push(node.textContent.trim());
                }
            }

            return textNodes.join('\\n');
        }''')

####Class to strictly verify the state after each action
class StateVerifier:
    """
    Enhanced StateVerifier that provides comprehensive state change detection
    with support for wait-for-stable-state, hierarchical state recognition,
    and progress enforcement.

    This class helps detect situations where an agent might incorrectly evaluate its progress,
    preventing infinite loops due to incorrect evaluations.
    """

    def __init__(self, similarity_threshold: float = 0.8, content_match_threshold: float = 0.7):
        """
        Initialize StateVerifier with configurable thresholds.

        Args:
            similarity_threshold: Value between 0.0 and 1.0 determining how similar
                                 content can be while still being considered "changed"
                                 (lower values = more strict change detection)
            content_match_threshold: Value between 0.0 and 1.0 determining how much of
                                    task content must be found to consider a page matching
        """
        self.similarity_threshold = similarity_threshold
        self.content_match_threshold = content_match_threshold
        self.last_verified_state = None
        self._recent_evaluations = []
        self._action_history = []
        self._last_state_time = time.time()
        self._last_stable_state = None
        self._hierarchical_state_cache = {}

    def compute_content_hash(self, state: Any) -> str:
        """
        Generate a hash of the relevant page content to detect changes.

        Args:
            state: Browser state containing element tree

        Returns:
            Hash string representing the content state
        """
        if not state or not hasattr(state, 'element_tree') or not state.element_tree:
            return "empty_state"

        # Extract visible text to detect content changes
        content = self.extract_visible_text(state.element_tree)
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def extract_visible_text(self, element_tree: Any, max_length: int = 5000) -> str:
        """
        Extract visible text from the DOM tree for comparison.

        Args:
            element_tree: DOM element tree to extract text from
            max_length: Maximum length of text to extract

        Returns:
            Extracted visible text
        """
        if not element_tree:
            return ""

        text_content = []

        # Extract text attribute if present
        if hasattr(element_tree, 'text') and element_tree.text:
            text_content.append(element_tree.text)

        # Extract from inner_text or textContent if present
        if hasattr(element_tree, 'inner_text') and element_tree.inner_text:
            text_content.append(element_tree.inner_text)

        # Extract from attributes that might contain visible text
        if hasattr(element_tree, 'attributes'):
            for attr_name in ['placeholder', 'value', 'alt', 'aria-label', 'title']:
                if attr_name in element_tree.attributes:
                    attr_value = element_tree.attributes[attr_name]
                    if attr_value and isinstance(attr_value, str):
                        text_content.append(attr_value)

        # Recursively extract from children
        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                child_text = self.extract_visible_text(child)
                if child_text:
                    text_content.append(child_text)

        result = " ".join(text_content)
        return result[:max_length]  # Limit text length for efficiency

    def calculate_content_similarity(self, pre_state: Any, post_state: Any) -> float:
        """
        Calculate rough similarity between two states (0.0 to 1.0).

        Args:
            pre_state: State before action
            post_state: State after action

        Returns:
            Similarity score from 0.0 (completely different) to 1.0 (identical)
        """
        # Extract text from both states
        pre_text = self.extract_visible_text(pre_state.element_tree if hasattr(pre_state, 'element_tree') else None)
        post_text = self.extract_visible_text(post_state.element_tree if hasattr(post_state, 'element_tree') else None)

        # Avoid division by zero
        if not pre_text or not post_text:
            return 0.0 if pre_text != post_text else 1.0

        # Basic similarity calculation
        if len(pre_text) > 100 and len(post_text) > 100:
            # For substantial content, compare sets of words for better accuracy
            pre_words = set(pre_text.lower().split())
            post_words = set(post_text.lower().split())

            # Calculate Jaccard similarity
            intersection = len(pre_words.intersection(post_words))
            union = len(pre_words.union(post_words))

            if union == 0:
                return 0.0

            return intersection / union
        else:
            # For minimal content, character-level comparison is more reliable
            longer = max(len(pre_text), len(post_text))
            shorter = min(len(pre_text), len(post_text))
            return shorter / longer if longer > 0 else 1.0

    def extract_form_fields(self, state: Any) -> Dict[str, str]:
        """
        Extract form fields and their values from the state.

        This helps detect changes in form inputs that might not
        significantly change the overall page content.

        Args:
            state: Browser state containing element tree

        Returns:
            Dictionary of form field identifiers and their values
        """
        fields = {}

        if not state or not hasattr(state, 'element_tree'):
            return fields

        def process_element(element):
            if not element:
                return

            is_input = False
            field_id = None
            field_value = None

            # Check if this is a form field element
            if hasattr(element, 'tag_name') and element.tag_name in ['input', 'textarea', 'select']:
                is_input = True

                # Get field identifier (prefer id, fall back to name, then to other attributes)
                if hasattr(element, 'attributes'):
                    for attr in ['id', 'name', 'data-testid', 'placeholder']:
                        if attr in element.attributes and element.attributes[attr]:
                            field_id = f"{element.tag_name}_{attr}_{element.attributes[attr]}"
                            break

                # If no identifier found, use element index
                if not field_id and hasattr(element, 'highlight_index'):
                    field_id = f"{element.tag_name}_{element.highlight_index}"

                # Get field value
                if hasattr(element, 'attributes') and 'value' in element.attributes:
                    field_value = element.attributes['value']
                elif hasattr(element, 'text'):
                    field_value = element.text

            # Add to fields dictionary if this is a form field
            if is_input and field_id:
                fields[field_id] = field_value or ""

            # Process children recursively
            if hasattr(element, 'children'):
                for child in element.children:
                    process_element(child)

        # Start recursive processing
        process_element(state.element_tree)
        return fields

    def detect_tab_change(self, pre_state: Any, post_state: Any) -> bool:
        """
        Detect if there was a tab change or panel change within the same page.

        This is particularly useful for single-page applications where
        navigation happens without URL changes.

        Args:
            pre_state: State before action
            post_state: State after action

        Returns:
            Boolean indicating if a tab/panel change was detected
        """
        # If URL changed, this isn't just a tab change
        if (hasattr(pre_state, 'url') and hasattr(post_state, 'url') and
                pre_state.url != post_state.url):
            return False

        # Get content hashes
        pre_hash = self.compute_content_hash(pre_state)
        post_hash = self.compute_content_hash(post_state)

        # Different content but same URL suggests tab/panel change
        if pre_hash != post_hash:
            # Calculate similarity to distinguish major vs. minor changes
            similarity = self.calculate_content_similarity(pre_state, post_state)

            # Tab changes typically result in significant content changes
            if similarity < self.similarity_threshold:
                # Check for certain tab-like UI patterns
                tab_indicators = self.detect_tab_ui_patterns(pre_state, post_state)
                if tab_indicators:
                    return True

                # Even without explicit tab UI, substantial content change
                # on same URL is likely a tab/panel/modal change
                return True

        return False

    def detect_tab_ui_patterns(self, pre_state: Any, post_state: Any) -> bool:
        """
        Check for UI patterns that suggest tab navigation occurred.

        Args:
            pre_state: State before action
            post_state: State after action

        Returns:
            Boolean indicating if tab UI patterns were detected
        """
        if not hasattr(pre_state, 'element_tree') or not hasattr(post_state, 'element_tree'):
            return False

        # Look for changes in aria-selected attributes (common in tabs)
        def find_selected_changes(element, selected_changes):
            if not element:
                return

            # Check for tab-like elements
            is_tab_like = False
            if hasattr(element, 'attributes'):
                # Check for typical tab attributes
                if ('role' in element.attributes and
                        element.attributes.get('role') in ['tab', 'tabpanel']):
                    is_tab_like = True

                # Check for aria-selected changes
                if 'aria-selected' in element.attributes:
                    selected_changes.append(element)

                # Check for active/selected classes
                if 'class' in element.attributes:
                    class_value = element.attributes['class']
                    if isinstance(class_value, str) and any(cls in class_value for cls in
                                                            ['active', 'selected', 'current']):
                        selected_changes.append(element)

            # Process children
            if hasattr(element, 'children'):
                for child in element.children:
                    find_selected_changes(child, selected_changes)

        # Find selection changes in both states
        pre_selected = []
        post_selected = []
        find_selected_changes(pre_state.element_tree, pre_selected)
        find_selected_changes(post_state.element_tree, post_selected)

        # If we found selection changes, likely a tab UI
        if pre_selected or post_selected:
            return True

        return False

    # ENHANCEMENT 1: Wait for stable state
    def verify_state_change_with_wait(self, pre_state: Any, post_state: Any,
                                      max_wait_time: float = 3.0) -> Tuple[bool, str]:
        """
        Verify state change with awareness of page loading and content stabilization.

        This method improves verification by considering loading states and waiting
        for content to stabilize before making a determination about state changes.

        Args:
            pre_state: State before action
            post_state: State after action
            max_wait_time: Maximum time to wait for state to stabilize (seconds)

        Returns:
            Tuple of (changed_significantly, reason)
        """
        # Check for loading indicators
        is_loading = self._is_page_loading(post_state)

        # If page is still loading, we wait before making a determination
        if is_loading:
            # In a real async implementation, we would await here
            # For our synchronous verification, we just note this state
            current_time = time.time()
            time_since_last_state = current_time - self._last_state_time

            # If we're still within max wait time, suggest waiting
            if time_since_last_state < max_wait_time:
                self._last_state_time = current_time
                return (False,
                        f"Page appears to be loading, waiting for stabilization ({time_since_last_state:.1f}s / {max_wait_time:.1f}s)")
            else:
                # We've waited long enough, proceed with evaluation
                logging.warning(f"Maximum wait time reached, proceeding with evaluation despite loading indicators")

        # Reset last state time
        self._last_state_time = time.time()

        # Store last stable state for future comparisons
        self._last_stable_state = post_state

        # Proceed with normal verification
        return self.verify_state_change(pre_state, post_state)

    def _is_page_loading(self, state: Any) -> bool:
        """
        Detect if a page appears to be in a loading state.

        Args:
            state: Current browser state

        Returns:
            Boolean indicating if the page appears to be loading
        """
        if not state or not hasattr(state, 'element_tree'):
            return False

        # Extract visible text to look for loading indicators
        content = self.extract_visible_text(state.element_tree).lower()

        # Common loading text indicators
        loading_texts = [
            'loading', 'please wait', 'loading...', 'wait',
            'processing', 'fetching', 'connecting'
        ]

        # Check for loading text indicators
        for indicator in loading_texts:
            if indicator in content:
                return True

        # Check for low interactive element count (might indicate loading)
        interactive_count = self.count_interactive_elements(state)
        if interactive_count < 3 and hasattr(state, 'url') and state.url != 'about:blank':
            # Few interactive elements might suggest still loading
            # But only if we're on a real page (not blank)
            return True

        return False

    # ENHANCEMENT 2: Hierarchical state recognition
    def detect_hierarchical_state(self, state: Any) -> Dict[str, Any]:
        """
        Detect hierarchical relationships in the DOM state.

        This helps recognize when the agent is simultaneously in multiple logical states,
        such as being in both the inbox and a specific tab within the inbox.

        Args:
            state: Current browser state

        Returns:
            Dictionary of hierarchical state information
        """
        if not state or not hasattr(state, 'element_tree'):
            return {'main': None, 'sub': []}

        # Cache results to avoid recomputation
        state_hash = self.compute_content_hash(state)
        if state_hash in self._hierarchical_state_cache:
            return self._hierarchical_state_cache[state_hash]

        hierarchical_info = {
            'main': None,  # Primary container (e.g., inbox)
            'sub': [],  # Sub-states (e.g., specific tabs)
            'active': [],  # Currently active states
            'indicators': {}  # Text indicators of each state
        }

        # Extract URL path components for primary state identification
        if hasattr(state, 'url'):
            url_parts = state.url.split('/')
            if len(url_parts) > 3:  # Skip http:// and domain
                hierarchical_info['main'] = url_parts[3].split('?')[0]  # Remove query params

        # Detect tabbed interfaces
        if hasattr(state, 'element_tree'):
            self._detect_tabbed_structure(state.element_tree, hierarchical_info)

        # Cache the results
        self._hierarchical_state_cache[state_hash] = hierarchical_info
        return hierarchical_info

    def _detect_tabbed_structure(self, element_tree: Any, hierarchical_info: Dict[str, Any]) -> None:
        """
        Detect tabbed interface structures in the DOM.

        Args:
            element_tree: DOM element tree
            hierarchical_info: Dictionary to update with hierarchical state info
        """
        if not element_tree:
            return

        # Check if this element might be a tab container
        is_tab_container = False
        tab_indicators = ['tabs', 'tablist', 'tabpanel', 'tab-container', 'tab-content']

        if hasattr(element_tree, 'attributes'):
            # Check for tab-related attributes
            if 'role' in element_tree.attributes and element_tree.attributes['role'] in ['tablist', 'tabs']:
                is_tab_container = True

            # Check for tab-related classes or IDs
            for attr in ['id', 'class']:
                if attr in element_tree.attributes:
                    attr_value = str(element_tree.attributes[attr]).lower()
                    if any(indicator in attr_value for indicator in tab_indicators):
                        is_tab_container = True

        # If this is a tab container, extract tab information
        if is_tab_container:
            tab_info = self._extract_tab_info(element_tree)
            if tab_info:
                hierarchical_info['sub'].extend(tab_info)

                # Identify active tabs
                for tab in tab_info:
                    if tab.get('active', False):
                        hierarchical_info['active'].append(tab['name'])

                        # Add text content of active tab as indicator
                        hierarchical_info['indicators'][tab['name']] = tab.get('content', '')

        # Process children recursively
        if hasattr(element_tree, 'children'):
            for child in element_tree.children:
                self._detect_tabbed_structure(child, hierarchical_info)

    def _extract_tab_info(self, tab_container: Any) -> List[Dict[str, Any]]:
        """
        Extract information about tabs from a tab container.

        Args:
            tab_container: Element that appears to be a tab container

        Returns:
            List of dictionaries containing tab information
        """
        tabs = []

        if not hasattr(tab_container, 'children'):
            return tabs

        # Process each potential tab element
        for child in tab_container.children:
            is_tab = False
            tab_info = {'name': '', 'active': False, 'content': '', 'index': -1}

            # Check if this might be a tab
            if hasattr(child, 'tag_name') and child.tag_name in ['li', 'div', 'button', 'a']:
                # Look for tab indicators
                if hasattr(child, 'attributes'):
                    # Check role attribute
                    if 'role' in child.attributes and child.attributes['role'] == 'tab':
                        is_tab = True

                    # Check if tab is active/selected
                    if ('aria-selected' in child.attributes and
                            child.attributes['aria-selected'] in ['true', True]):
                        tab_info['active'] = True

                    # Check class for 'active' indicators
                    if 'class' in child.attributes:
                        class_value = str(child.attributes['class']).lower()
                        if any(indicator in class_value for indicator in ['active', 'selected', 'current']):
                            tab_info['active'] = True

                    # Extract tab name
                    for attr in ['aria-label', 'title', 'name']:
                        if attr in child.attributes and child.attributes[attr]:
                            tab_info['name'] = child.attributes[attr]
                            is_tab = True
                            break

                # Extract text content as tab name if not found in attributes
                if not tab_info['name'] and hasattr(child, 'text') and child.text:
                    tab_info['name'] = child.text.strip()
                    is_tab = True

                # Use child index as fallback name
                if not tab_info['name'] and hasattr(child, 'highlight_index'):
                    tab_info['index'] = child.highlight_index
                    tab_info['name'] = f"Tab {child.highlight_index}"
                    is_tab = True

                # If this looks like a tab and has a name, add it to the list
                if is_tab and tab_info['name']:
                    # Extract tab content if available
                    if hasattr(child, 'children'):
                        content_text = self.extract_visible_text(child)
                        tab_info['content'] = content_text

                    tabs.append(tab_info)

        return tabs

    # ENHANCEMENT 3: Progress enforcement mechanism
    def enforce_progress(self, action_history: List[Dict[str, Any]],
                         current_state: Any, task_goal: str = None) -> Tuple[bool, str]:
        """
        Detect when the agent is stuck in a loop and determine if progress enforcement is needed.

        This acts as a safety net when normal verification fails to break loops.

        Args:
            action_history: List of recent actions and their results
            current_state: Current browser state
            task_goal: Description of what the agent is trying to achieve

        Returns:
            Tuple of (should_enforce_progress, guidance_message)
        """
        # Update action history
        self._action_history = action_history[-10:] if len(action_history) > 10 else action_history

        # Check for repeated actions
        repeated_actions = self._detect_repeated_actions()
        if repeated_actions:
            return (
            True, f"Detected a loop of repeated actions: {repeated_actions}. Try a completely different approach.")

        # Check for lack of progress despite actions
        if len(self._action_history) >= 3:
            progress_made = self._evaluate_progress(task_goal)
            if not progress_made:
                return (True,
                        "No progress detected after multiple actions. Consider a different strategy or proceed to the next logical step.")

        # Check for hierarchical state conflicts
        if current_state:
            hierarchical_info = self.detect_hierarchical_state(current_state)

            # If we're in multiple states simultaneously (like inbox + specific tab)
            if len(hierarchical_info['active']) > 0:
                active_states = ", ".join(hierarchical_info['active'])
                return (False,
                        f"You are currently in multiple contexts: {hierarchical_info['main']} and {active_states}. Focus on the next step within the current active context.")

        # No progress enforcement needed
        return (False, "")

    def _detect_repeated_actions(self) -> str:
        """
        Detect repeated actions in the action history.

        Returns:
            Description of repeated actions or empty string if none detected
        """
        if len(self._action_history) < 3:
            return ""

        # Extract action types
        action_types = []
        for action in self._action_history:
            if 'type' in action:
                action_types.append(action['type'])

        # Check for same action repeated
        if len(action_types) >= 3:
            last_three = action_types[-3:]
            if last_three.count(last_three[0]) == 3:
                return last_three[0]

        # Check for alternating patterns
        if len(action_types) >= 4:
            if action_types[-1] == action_types[-3] and action_types[-2] == action_types[-4]:
                return f"{action_types[-1]} → {action_types[-2]}"

        return ""

    def _evaluate_progress(self, task_goal: str = None) -> bool:
        """
        Evaluate if the agent is making progress toward the goal.

        Args:
            task_goal: Description of what the agent is trying to achieve

        Returns:
            Boolean indicating if progress appears to be occurring
        """
        if not self._action_history or len(self._action_history) < 2:
            return True  # Not enough history to determine lack of progress

        # Check for success indicators in recent actions
        success_indicators = ['success', 'completed', 'found', 'navigated']

        for action in self._action_history[-2:]:
            if 'result' in action:
                result = action['result'].lower()
                if any(indicator in result for indicator in success_indicators):
                    return True

        # Check if we're getting closer to goal based on keywords
        if task_goal and hasattr(self, '_last_stable_state') and self._last_stable_state:
            goal_keywords = self._extract_keywords(task_goal)
            if not goal_keywords:
                return True  # No keywords to match

            # Get current page content
            content = self.extract_visible_text(self._last_stable_state.element_tree)

            # Count matching keywords
            matches = sum(1 for keyword in goal_keywords if keyword in content.lower())

            # If we match more than half of the keywords, consider it progress
            if matches >= len(goal_keywords) // 2:
                return True

        return False

    def verify_state_change(self, pre_state: Any, post_state: Any) -> Tuple[bool, str]:
        """
        Verify if a meaningful state change occurred after an action.

        Args:
            pre_state: State before action
            post_state: State after action

        Returns:
            Tuple of (changed_significantly, reason)
        """
        # Check for None states
        if not pre_state or not post_state:
            return (True, "One of the states is None")

            # URL change is a strong indicator of navigation
        pre_url = getattr(pre_state, 'url', '')
        post_url = getattr(post_state, 'url', '')
        if pre_url != post_url:
            return (True, f"URL changed from {pre_url} to {post_url}")

        # Title change can indicate dynamic content updates
        pre_title = getattr(pre_state, 'title', '')
        post_title = getattr(post_state, 'title', '')
        if pre_title != post_title:
            return (True, f"Title changed from '{pre_title}' to '{post_title}'")

        # Check for tab/panel change within same page
        if self.detect_tab_change(pre_state, post_state):
            return (True, "Tab or panel changed within the same page")

        # Track form field changes
        pre_fields = self.extract_form_fields(pre_state)
        post_fields = self.extract_form_fields(post_state)

        # Check if any form fields were modified
        if pre_fields != post_fields:
            changed_fields = []
            for field_id, value in post_fields.items():
                if field_id in pre_fields and pre_fields[field_id] != value:
                    changed_fields.append(field_id)

            if changed_fields:
                return (True, f"Form fields changed: {', '.join(changed_fields)}")

        # Check hierarchical state changes that might not affect content hash
        pre_hierarchical = self.detect_hierarchical_state(pre_state)
        post_hierarchical = self.detect_hierarchical_state(post_state)

        if pre_hierarchical['active'] != post_hierarchical['active']:
            pre_active = ", ".join(pre_hierarchical['active']) if pre_hierarchical['active'] else "none"
            post_active = ", ".join(post_hierarchical['active']) if post_hierarchical['active'] else "none"
            return (True, f"Active tab/panel changed from '{pre_active}' to '{post_active}'")

        # Content hash change indicates DOM updates
        pre_hash = self.compute_content_hash(pre_state)
        post_hash = self.compute_content_hash(post_state)

        if pre_hash != post_hash:
            # Calculate similarity to detect minor vs major changes
            similarity = self.calculate_content_similarity(pre_state, post_state)
            if similarity < self.similarity_threshold:  # Less than threshold means significant change
                return (True, f"Content significantly changed (similarity: {similarity:.2f})")
            else:
                return (False, f"Only minor content change detected (similarity: {similarity:.2f})")

        # Check for new interactive elements which might indicate progress
        pre_interactive = self.count_interactive_elements(pre_state)
        post_interactive = self.count_interactive_elements(post_state)

        if post_interactive > pre_interactive:
            return (True, f"New interactive elements appeared ({pre_interactive} → {post_interactive})")

        # No significant change detected
        return (False, "No significant state change detected")

    def count_interactive_elements(self, state: Any) -> int:
        """
        Count interactive elements in the state.

        Args:
            state: Browser state containing element tree

        Returns:
            Number of interactive elements
        """
        count = 0

        if not state or not hasattr(state, 'element_tree'):
            return count

        def process_element(element):
            nonlocal count

            # Skip non-visible elements
            if hasattr(element, 'is_visible') and not element.is_visible:
                return

            # Check if this is an interactive element
            is_interactive = False

            if hasattr(element, 'tag_name'):
                # Direct interactive elements
                if element.tag_name in ['a', 'button', 'input', 'select', 'textarea']:
                    is_interactive = True

                # Elements with specific roles
                elif hasattr(element, 'attributes') and 'role' in element.attributes:
                    role = element.attributes['role']
                    if role in ['button', 'link', 'checkbox', 'radio', 'menuitem', 'tab']:
                        is_interactive = True

                # Elements with click handlers
                elif hasattr(element, 'attributes') and any(attr.startswith('on') for attr in element.attributes):
                    is_interactive = True

            if is_interactive:
                count += 1

            # Process children recursively
            if hasattr(element, 'children'):
                for child in element.children:
                    process_element(child)

        # Start recursive processing
        process_element(state.element_tree)
        return count

    def evaluate_action_success(self, pre_state: Any, post_state: Any, action_type: str) -> Tuple[bool, str]:
        """
        Evaluate if an action was successful based on expected state changes.

        Args:
            pre_state: State before action
            post_state: State after action
            action_type: Type of action performed (e.g., 'click', 'type', 'navigate')

        Returns:
            Tuple of (success, reason)
        """
        # First check if we need to wait for stable state
        if self._is_page_loading(post_state):
            return (False, "Page appears to be loading, evaluation deferred")

        # Check for hierarchical state changes that might not affect content
        if action_type in ['click', 'click_element']:
            pre_hierarchical = self.detect_hierarchical_state(pre_state)
            post_hierarchical = self.detect_hierarchical_state(post_state)

            if pre_hierarchical['active'] != post_hierarchical['active']:
                return (True, f"Successfully changed active tab/panel")

        # First check for general state changes
        changed, reason = self.verify_state_change(pre_state, post_state)

        # For navigation actions, URL must change
        if action_type in ['navigate', 'go_to_url', 'go_back', 'go_forward']:
            pre_url = getattr(pre_state, 'url', '')
            post_url = getattr(post_state, 'url', '')
            if pre_url == post_url:
                return (False, f"Navigation action did not change URL from {pre_url}")
            return (True, f"Successfully navigated to {post_url}")

            # For click actions, expect some change unless it's a toggle that returned to original state
        elif action_type in ['click', 'click_element']:
            if not changed:
                # Check if it might be a toggle action that reverted to original state
                pre_hash = self.compute_content_hash(pre_state)
                post_hash = self.compute_content_hash(post_state)

                if pre_hash == post_hash:
                    # Check hierarchical states - we might have clicked a tab that's already active
                    pre_hierarchical = self.detect_hierarchical_state(pre_state)
                    post_hierarchical = self.detect_hierarchical_state(post_state)

                    if post_hierarchical['active'] and set(post_hierarchical['active']) == set(
                            pre_hierarchical['active']):
                        return (True, f"Clicked an already active tab/panel: {', '.join(post_hierarchical['active'])}")
                    else:
                        return (False, "Click action produced no visible change")
            return (changed, reason)

            # For type actions, form fields should change
        elif action_type in ['type', 'fill', 'input_text']:
            pre_fields = self.extract_form_fields(pre_state)
            post_fields = self.extract_form_fields(post_state)

            if pre_fields == post_fields:
                return (False, "Text input action did not change any form fields")
            return (True, "Successfully updated form field(s)")

            # For general actions, any significant change indicates success
        return (changed, reason)

    def _extract_keywords(self, text: str) -> list:
        """Extract meaningful keywords from text, filtering out common words."""
        if not text:
            return []

        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

        # Filter out common words
        stopwords = {'this', 'that', 'these', 'those', 'with', 'from', 'have', 'will',
                     'about', 'should', 'could', 'would', 'their', 'there', 'where',
                     'which', 'when', 'what', 'page', 'click', 'browser', 'navigate'}

        keywords = [word for word in words if word not in stopwords]
        return keywords

    def is_likely_target_page(self, state: Any, task_goal: str = None) -> bool:
        """
        Determine if the current page is likely to be the target page the agent is looking for.

        Args:
            state: Current browser state
            task_goal: Description of what the agent is trying to achieve

        Returns:
            True if this appears to be the target page
        """
        if not task_goal or not state:
            return False

        # Check URL for relevant keywords from the task
        if hasattr(state, 'url') and state.url:
            task_keywords = self._extract_keywords(task_goal)
            url_lower = state.url.lower()

            # Count matching keywords in URL
            url_keyword_matches = sum(1 for keyword in task_keywords if keyword in url_lower)
            if url_keyword_matches >= 2 and len(task_keywords) >= 3:
                return True

        # Check page content for task-relevant information
        if hasattr(state, 'element_tree'):
            content = self.extract_visible_text(state.element_tree)
            task_keywords = self._extract_keywords(task_goal)

            # Count matching keywords in content
            content_keyword_matches = sum(1 for keyword in task_keywords if keyword in content.lower())
            if content_keyword_matches >= len(task_keywords) * self.content_match_threshold:
                return True

        # Check hierarchical state for relevance to task
        hierarchical_info = self.detect_hierarchical_state(state)
        if hierarchical_info['active'] and task_goal:
            # Check if any active tab matches task keywords
            task_keywords = self._extract_keywords(task_goal)

            for active_tab in hierarchical_info['active']:
                active_tab_lower = active_tab.lower()
                matches = sum(1 for keyword in task_keywords if keyword in active_tab_lower)

                # If tab name matches task keywords, likely the right tab
                if matches >= 1 and len(task_keywords) >= 2:
                    return True

        return False

    def is_repeated_evaluation(self, evaluation: str) -> bool:
        """
        Check if this evaluation is repeating, suggesting a potential loop.

        Args:
            evaluation: Current evaluation string

        Returns:
            True if this appears to be a repeated evaluation
        """
        # Clean up evaluation for comparison
        clean_eval = re.sub(r'[^a-zA-Z0-9\s]', '', evaluation.lower())

        # Check if this evaluation is very similar to recent ones
        for recent_eval in self._recent_evaluations:
            if self._strings_similar(clean_eval, recent_eval):
                return True

        # Update recent evaluations list (keep last 3)
        self._recent_evaluations.append(clean_eval)
        if len(self._recent_evaluations) > 3:
            self._recent_evaluations.pop(0)

        return False

    def _strings_similar(self, str1: str, str2: str) -> bool:
        """Check if two strings are highly similar."""
        # Simple similarity check - could be enhanced with better algorithms
        if len(str1) == 0 or len(str2) == 0:
            return False

        # Compare sets of words
        words1 = set(str1.split())
        words2 = set(str2.split())

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        if union == 0:
            return False

        similarity = intersection / union
        return similarity > 0.7  # 70% similarity threshold

    def should_override_evaluation(self, current_eval: str, pre_state: Any, post_state: Any,
                                   action_type: str = None, task_goal: str = None) -> Tuple[bool, str]:
        """
        Determine if the current evaluation should be overridden, with enhanced accuracy.
        This addresses both false success claims and false failure claims.

        Args:
            current_eval: Current evaluation string from the agent
            pre_state: State before action
            post_state: State after action
            action_type: Type of action performed
            task_goal: Description of what the agent is trying to achieve

        Returns:
            Tuple of (should_override, new_evaluation)
        """
        # First check if page is still loading
        if self._is_page_loading(post_state):
            return (True, "In progress: Page is still loading, will evaluate when stable")

        # Get actual success info based on state changes
        success, reason = self.verify_state_change_with_wait(pre_state, post_state)

        # For click actions, we might already be on the target tab
        if action_type in ['click', 'click_element'] and not success:
            # Get hierarchical state info
            hierarchical_info = self.detect_hierarchical_state(post_state)

            # If we have active tabs and they match the task goal
            if hierarchical_info['active'] and task_goal:
                # Check if any active tab matches task keywords
                task_keywords = self._extract_keywords(task_goal)

                for active_tab in hierarchical_info['active']:
                    tab_lower = active_tab.lower()
                    matches = sum(1 for keyword in task_keywords if keyword in tab_lower)

                    # If tab name matches task keywords, likely already on right tab
                    if matches >= 1 and len(task_keywords) >= 2:
                        return (True, f"Success: Already on the correct tab '{active_tab}'")

        # CASE 1: DISABLED - This was causing infinite loops!
        # Problem: Agent opens email, reads it, goes back to inbox.
        # Pre-state = inbox, Post-state = inbox (after going back)
        # verify_state_change() returns False (states look similar)
        # But the action WAS successful! Agent correctly says "Success: opened email 1"
        # This code was INCORRECTLY overriding success to failure.
        # State change detection ≠ action success. Disabled 2026-01-17.
        # if current_eval and "success" in current_eval.lower() and not success:
        #     new_eval = f"Failed: {reason}"
        #     return (True, new_eval)

        # CASE 2: Current evaluation indicates failure but we may have succeeded
        if current_eval and "fail" in current_eval.lower():
            # Check if we might be on the right page already
            if self.is_likely_target_page(post_state, task_goal):
                new_eval = f"Success: Target page or content already reached."
                return (True, new_eval)

            # Check if this might be a tab change within the same page
            if self.detect_tab_change(pre_state, post_state):
                new_eval = f"Success: Tab or panel changed within the page."
                return (True, new_eval)

            # Check hierarchical state to see if we're already on the right tab
            hierarchical_info = self.detect_hierarchical_state(post_state)
            if hierarchical_info['active'] and task_goal:
                active_tabs = ", ".join(hierarchical_info['active'])
                if any(kw in active_tabs.lower() for kw in self._extract_keywords(task_goal)):
                    new_eval = f"Success: Already on the correct tab '{active_tabs}'"
                    return (True, new_eval)

            # Check if we're seeing the same failure repeatedly (possible loop)
            if self.is_repeated_evaluation(current_eval):
                new_eval = f"Warning: Repeated failure detected. Consider trying a completely different approach."
                return (True, new_eval)

        # If no clear evaluation but we detected success/failure, provide one
        if not current_eval or current_eval.strip() == "":
            if success:
                new_eval = f"Success: {reason}"
            else:
                new_eval = f"Failed: {reason}"
            return (True, new_eval)

        return (False, current_eval)

###########Emergency and forceful loop breaker
class LoopBreaker:
    """
    LoopBreaker provides aggressive intervention mechanisms to forcibly break
    infinite loops when more subtle interventions have failed.

    This class detects various loop patterns and implements emergency actions
    to break out of them. It's designed to be called when standard evaluation
    overrides have not successfully changed the agent's behavior.
    """

    def __init__(self):
        """Initialize the LoopBreaker with tracking state."""
        self.override_count = 0
        self.last_override_time = time.time()
        self.override_history = []
        self.action_history = []
        self.evaluation_history = []
        self.last_intervention = None
        self.intervention_count = 0
        # Add these two lines to fix warnings:
        self._last_state = None
        self._last_state_time = time.time()

    def track_override(self, original_eval: str, new_eval: str) -> None:
        """
        Track an evaluation override to detect when overrides aren't working.

        Args:
            original_eval: The original evaluation
            new_eval: The new evaluation after override
        """
        current_time = time.time()

        # Reset count if it's been a while since last override
        if current_time - self.last_override_time > 60:  # 60 seconds
            self.override_count = 0
            self.override_history = []

        self.override_count += 1
        self.last_override_time = current_time
        self.override_history.append((original_eval, new_eval, current_time))

        # Trim history to last 10 overrides
        if len(self.override_history) > 10:
            self.override_history = self.override_history[-10:]


    def track_action(self, action: Any, evaluation: str) -> None:
        """
        Track an action and its evaluation to detect action patterns.

        Args:
            action: The action that was executed
            evaluation: The evaluation of that action
        """
        self.action_history.append((action, time.time()))
        self.evaluation_history.append(evaluation)

        # Trim histories to last 20 items
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
        if len(self.evaluation_history) > 20:
            self.evaluation_history = self.evaluation_history[-20:]

    def get_consecutive_override_count(self) -> int:
        """Get count of consecutive failed overrides of the same type."""
        if len(self.override_history) < 2:
            return 0

        # Count consecutive similar overrides
        count = 0
        last_orig, last_new, _ = self.override_history[-1]

        for i in range(len(self.override_history) - 2, -1, -1):
            orig, new, _ = self.override_history[i]
            if self._are_evals_similar(orig, last_orig) and self._are_evals_similar(new, last_new):
                count += 1
            else:
                break

        return count

    def _are_evals_similar(self, eval1: str, eval2: str) -> bool:
        """Check if two evaluations are semantically similar."""
        if not eval1 or not eval2:
            return False

        # Clean and normalize strings
        eval1 = re.sub(r'[^\w\s]', '', eval1.lower())
        eval2 = re.sub(r'[^\w\s]', '', eval2.lower())

        # Compare sets of words
        words1 = set(eval1.split())
        words2 = set(eval2.split())

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        similarity = intersection / union if union > 0 else 0
        return similarity > 0.7  # 70% similar means essentially the same eval

    def detect_persistent_loop(self) -> Tuple[bool, str]:
        """
        Detect if the agent is stuck in a persistent loop despite overrides.

        Returns:
            Tuple of (is_loop_detected, loop_type)
        """
        ###Detect perpetual_loading
        if hasattr(self, '_last_state_time') and time.time() - getattr(self, '_last_state_time', 0) > 120:
            if hasattr(self, '_last_state') and StateVerifier()._is_page_loading(getattr(self, '_last_state', None)):
                return True, "perpetual_loading"
        ###Linux Change 2 Start###
        # Add platform-specific detection logic
        system = get_platform()

        # Normalize evaluation strings for consistent cross-platform comparison
        normalized_evals = []
        if len(self.evaluation_history) >= 4:
            for eval_str in self.evaluation_history[-4:]:
                if eval_str:
                    # Remove platform-specific line endings and extra whitespace
                    norm_eval = eval_str.replace('\r\n', '\n').replace('\r', '\n')
                    norm_eval = ' '.join(norm_eval.split())  # Normalize whitespace
                    normalized_evals.append(norm_eval)
        ###Linux Change 2 End###

        # Check if we've had multiple consecutive overrides of same type
        consecutive_overrides = self.get_consecutive_override_count()
        if consecutive_overrides >= 2:
            return True, "persistent_override_loop"

        # Check for repeated evaluation patterns
        if len(self.evaluation_history) >= 4:
            recent_evals = self.evaluation_history[-4:]
            # Look for alternating eval patterns (Success, Fail, Success, Fail)
            success_pattern = [True if "success" in e.lower() else False for e in recent_evals]
            if success_pattern in ([True, False, True, False], [False, True, False, True]):
                return True, "alternating_eval_loop"

            # Check for repeated same evaluations
            if len(set(recent_evals[-3:])) == 1:
                return True, "same_eval_loop"

        # Check for click loops on same element
        click_targets = []
        for action, _ in self.action_history[-5:]:
            # Extract click targets from actions (adjust based on your action structure)
            target = self._extract_click_target(action)
            if target:
                click_targets.append(target)

        if len(click_targets) >= 3 and len(set(click_targets[-3:])) == 1:
            return True, "repeated_click_loop"

        return False, ""

    def _extract_click_target(self, action: Any) -> Any:
        """
        Extract the target of a click action.
        Customize this based on your action structure.
        """
        try:
            # Try different approaches to get the click target based on action structure
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
                if 'click' in action_dict:
                    return action_dict['click'].get('element_index')
                elif 'click_element' in action_dict:
                    return action_dict['click_element'].get('element_index')

            # Direct attribute access approach
            if hasattr(action, 'click'):
                if hasattr(action.click, 'element_index'):
                    return action.click.element_index

            # For list of actions
            if isinstance(action, list) and len(action) > 0:
                for a in action:
                    target = self._extract_click_target(a)
                    if target:
                        return target

        except Exception:
            pass

        return None

    def force_break_loop(self, loop_type: str, current_state: Any = None) -> Dict[str, Any]:
        """
        Generate a forceful intervention to break out of a detected loop.

        Args:
            loop_type: The type of loop detected
            current_state: The current browser state (optional)

        Returns:
            Dictionary with override action and message
        """
        # Track intervention
        self.intervention_count += 1
        self.last_intervention = time.time()

        # General emergency actions
        emergency_actions = [
            {
                "action_type": "refresh_page",
                "message": "EMERGENCY: Forcing page refresh to break loop"
            },
            {
                "action_type": "go_back",
                "message": "EMERGENCY: Navigating back to previous page to break loop"
            },
            {
                "action_type": "scroll_down",
                "message": "EMERGENCY: Scrolling down to reveal different content"
            },
            {
                "action_type": "stop_current_task",
                "message": "EMERGENCY: Abandoning current subtask and moving to next task component"
            }
        ]

        # Choose intervention based on loop type and intervention count
        if loop_type == "persistent_override_loop":
            # For persistent override loops, try more dramatic interventions
            action_index = min(self.intervention_count - 1, len(emergency_actions) - 1)
            action = emergency_actions[action_index]
            return {
                "override_action": action["action_type"],
                "override_message": f"{action['message']}. Multiple evaluation overrides failed to break loop."
            }

        elif loop_type == "repeated_click_loop":
            return {
                "override_action": "scroll_down",
                "override_message": "EMERGENCY: Detected clicking loop on same element. Scrolling to reveal different content."
            }

        elif loop_type == "alternating_eval_loop":
            return {
                "override_action": "go_back",
                "override_message": "EMERGENCY: Detected alternating success/failure pattern. Returning to previous stable state."
            }

        elif loop_type == "same_eval_loop":
            return {
                "override_action": "refresh_page" if self.intervention_count % 2 == 0 else "go_back",
                "override_message": "EMERGENCY: Multiple identical evaluations detected. Resetting page state to break the pattern."
            }

        if loop_type == "perpetual_loading":
            self._last_state = current_state
            self._last_state_time = time.time()

            return {
                "override_action": "new_tab",
                "override_message": "EMERGENCY: Page appears to be perpetually loading. Creating new tab and closing problematic one."
            }

        # Default emergency action (rotate through options based on intervention count)
        action_index = self.intervention_count % len(emergency_actions)
        action = emergency_actions[action_index]
        return {
            "override_action": action["action_type"],
            "override_message": f"{action['message']}. Taking emergency action to break potential loop."
        }

    def create_emergency_action(self, action_type: str) -> Any:
        """
        Create an action object for emergency interventions.

        This method converts high-level action types like 'refresh_page' into
        specific action objects that your agent can execute.

        Args:
            action_type: High-level action type (refresh_page, go_back, etc.)

        Returns:
            Action object compatible with your agent's controller
        """
        # This method needs to be customized based on your action model structure
        if action_type == "refresh_page":
            # Create a refresh page action
            return {"refresh": {}}

        elif action_type == "go_back":
            # Create a go back action
            return {"go_back": {}}

        elif action_type == "scroll_down":
            # Create a scroll down action
            return {"scroll": {"direction": "down", "amount": "medium"}}

        elif action_type == "stop_current_task":
            # This might need to be handled at a higher level
            # For now, just return a no-op action
            return {"extract_content": {"type": "page_content"}}

        # Default action - extract content (relatively safe)
        return {"extract_content": {"type": "page_content"}}

    def check_and_break_loop(self, pre_state: Any, post_state: Any, model_output: Any, last_result: Any) -> Tuple[
        bool, Any, Any]:
        """
        Check for loops and apply emergency interventions if needed.
        This is the main integration point with the agent's step() method.

        Args:
            pre_state: State before action
            post_state: State after action
            model_output: Current model output with evaluation
            last_result: Results from the last action

        Returns:
            Tuple of (intervention_applied, updated_model_output, updated_last_result)
        """
        # First check if we should intervene
        if not self.should_emergency_intervene():
            return False, model_output, last_result

        # Detect specific loop type
        is_loop, loop_type = self.detect_persistent_loop()
        if not is_loop:
            return False, model_output, last_result

        # Get intervention details
        intervention = self.force_break_loop(loop_type, post_state)

        # Update model output evaluation with emergency message
        if model_output and hasattr(model_output, 'current_state') and hasattr(model_output.current_state,
                                                                               'evaluation_previous_goal'):
            model_output.current_state.evaluation_previous_goal = f"EMERGENCY OVERRIDE: {intervention['override_message']}"

        # Add clear message to result
        if isinstance(last_result, list) and last_result:
            existing_content = last_result[-1].extracted_content if hasattr(last_result[-1],
                                                                            'extracted_content') else ""
            emergency_message = f"\n\n⚠️ EMERGENCY LOOP INTERVENTION ⚠️\n{intervention['override_message']}\nTaking emergency action: {intervention['override_action']}"

            if existing_content:
                combined_content = f"{existing_content}\n\n{emergency_message}"
            else:
                combined_content = emergency_message

            last_result[-1].extracted_content = combined_content

        # Log the emergency intervention
        logging.warning(f"🚨 EMERGENCY LOOP INTERVENTION: {intervention['override_message']}")

        return True, model_output, last_result

    def should_emergency_intervene(self) -> bool:
        """
        Determine if emergency intervention is needed based on override history.

        Returns:
            Boolean indicating if emergency intervention should be applied
        """
        # Intervene if we've had multiple consecutive overrides
        if self.get_consecutive_override_count() >= 2:
            return True

        # Check if we're in a rapid override situation
        if len(self.override_history) >= 3:
            # If we've had 3+ overrides in the last 2 minutes
            recent_time = time.time() - 120  # 2 minutes ago
            recent_overrides = [o for o in self.override_history if o[2] > recent_time]
            if len(recent_overrides) >= 3:
                return True

        # Check for repeated identical evaluations
        if len(self.evaluation_history) >= 3:
            if len(set(self.evaluation_history[-3:])) == 1:
                return True

        return False

    def handle_loading_timeout(self, browser_context, current_state) -> bool:
        """Create new tab and close problematic loading tab."""
        # Use existing _is_page_loading method
        is_loading = StateVerifier()._is_page_loading(current_state)  # Use existing function
        if not is_loading:
            return False

        try:
            logging.warning("🔄 Perpetual loading detected - creating new tab")
            asyncio.create_task(browser_context.create_new_tab())
            asyncio.sleep(0.5)

            if browser_context.session and browser_context.session.current_page:
                logging.warning("🔄 Closing problematic loading tab")
                asyncio.create_task(browser_context.close_current_tab())
                return True
        except Exception as e:
            logging.error(f"❌ Error handling loading timeout: {str(e)}")

        return False