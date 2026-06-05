# vision_ragcore_activememory.py - Active Vision Memory Layer
# Transforms passive vision storage into active, brain-like visual memory
# Implements asymptotic dynamics, emotion detection, and temporal-frequency boosting

import time
import math
import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from PIL import Image

# Import the base RAG core
try:
    from .vision_ragcore import get_vision_rag_instance, VisionMemoryItem
    print("✅ Successfully imported Vision RAG foundation module")
except ImportError as e:
    print(f"❌ Failed to import vision_ragcore: {e}")
    print("❌ Active memory module requires the base Vision RAG system to function")
    raise


class AsymptoticMemoryManager:
    """
    Implements asymptotic storage and decay mathematics
    Ensures memories:
    - Never stored at 100% (storage ceiling)
    - Never decay to 0% (decay floor)
    - Gradual compression over time (asymptotic curves)
    """

    def __init__(self, config: Dict):
        self.storage_ceiling = config['asymptotic_dynamics'].get('storage_ceiling',
                                                                  config['storage']['storage_ceiling'])
        self.decay_floor = config['asymptotic_dynamics']['decay_floor']
        self.decay_halflife_days = config['asymptotic_dynamics']['decay_halflife_days']
        self.frequency_boost_factor = config['asymptotic_dynamics']['frequency_boost_factor']
        self.max_frequency_boost = config['asymptotic_dynamics']['max_frequency_boost']

        print(f"📐 AsymptoticMemoryManager initialized:")
        print(f"   Storage ceiling: {self.storage_ceiling} (never 100%)")
        print(f"   Decay floor: {self.decay_floor} (never 0%)")
        print(f"   Decay halflife: {self.decay_halflife_days} days")

    def calculate_storage_strength(self, clip_similarity: float) -> float:
        """
        Apply storage ceiling to prevent 100% storage
        Formula: similarity × storage_ceiling

        Examples:
        - similarity=1.00 → 0.95 (never 100%)
        - similarity=0.92 → 0.87

        Args:
            clip_similarity: Raw CLIP similarity in [0, 1]

        Returns: Compressed storage strength in [0, storage_ceiling]
        """
        storage_strength = clip_similarity * self.storage_ceiling
        return storage_strength

    def calculate_decay_factor(self, days_old: float) -> float:
        """
        Exponential decay with asymptotic floor
        Formula: floor + (1 - floor) × e^(-days_old / halflife)

        Properties:
        - days=0   → 1.00 (full strength)
        - days=30  → 0.505 (half-life)
        - days=365 → 0.010 (approaches floor)
        - days=∞   → 0.01 (never reaches 0)

        Args:
            days_old: Age of memory in days

        Returns: Decay factor in [decay_floor, 1.0]
        """
        decay = self.decay_floor + (1.0 - self.decay_floor) * \
                math.exp(-days_old / self.decay_halflife_days)
        return decay

    def calculate_frequency_boost(self, access_count: int) -> float:
        """
        Logarithmic frequency boost with cap
        Formula: 1.0 + min(ln(1 + count) × factor, max - 1.0)

        Properties:
        - count=0   → 1.0 (no boost)
        - count=10  → 2.2
        - count=100 → 3.0 (cap)

        Args:
            access_count: Number of times memory accessed

        Returns: Frequency boost in [1.0, max_frequency_boost]
        """
        if access_count == 0:
            return 1.0

        boost = 1.0 + min(
            math.log(1 + access_count) * self.frequency_boost_factor,
            self.max_frequency_boost - 1.0
        )
        return boost

    def calculate_memory_strength(self, memory: VisionMemoryItem, current_time: float) -> float:
        """
        Calculate current memory strength with all factors

        Factors:
        1. Stored strength (base, ≤ storage_ceiling)
        2. Time decay (asymptotic, floor = decay_floor)
        3. Frequency boost (logarithmic, cap = max_frequency_boost)

        Args:
            memory: VisionMemoryItem object
            current_time: Current Unix timestamp

        Returns: Final strength for ranking
        """
        # Base strength (already compressed during storage)
        base_strength = memory.stored_strength

        # Time decay
        days_old = (current_time - memory.timestamp) / 86400
        time_factor = self.calculate_decay_factor(days_old)

        # Frequency boost
        freq_factor = self.calculate_frequency_boost(memory.access_count)

        # Combined strength (multiplicative)
        final_strength = base_strength * time_factor * freq_factor

        return final_strength


class EmotionKeywordDetector:
    """
    Detects emotion-based permanence keywords in CHAT_MODE
    Provides strong boost for user preferences/rules
    Prevents false positives in ACTION_MODE
    """

    def __init__(self, config: Dict):
        self.emotion_boost_factor = config['emotion_keywords']['emotion_boost_factor']
        self.enabled_modes = config['emotion_keywords']['enabled_modes']
        self.keywords = [kw.lower() for kw in config['emotion_keywords']['keywords']]

        print(f"💭 EmotionKeywordDetector initialized:")
        print(f"   Boost factor: {self.emotion_boost_factor}x")
        print(f"   Enabled modes: {self.enabled_modes}")
        print(f"   Keywords: {self.keywords}")

    def detect_keywords(self, text: str, mode: str) -> List[str]:
        """
        Detect emotion keywords in text (case-insensitive)
        Only active for CHAT_MODE to prevent false positives

        Args:
            text: Text to analyze
            mode: "CHAT_MODE" or "ACTION_MODE"

        Returns: List of detected keywords
        """
        if mode not in self.enabled_modes:
            return []

        text_lower = text.lower()
        detected = []

        for keyword in self.keywords:
            if keyword in text_lower:
                detected.append(keyword)

        if detected and mode in self.enabled_modes:
            print(f"💭 EMOTION KEYWORDS DETECTED ({mode}): {detected}")

        return detected

    def calculate_emotion_boost(self, emotion_keywords: List[str], mode: str) -> float:
        """
        Calculate emotion boost factor
        Returns: boost_factor if CHAT_MODE and keywords present, else 1.0

        Args:
            emotion_keywords: List of detected keywords
            mode: "CHAT_MODE" or "ACTION_MODE"

        Returns: Boost multiplier
        """
        if mode not in self.enabled_modes or not emotion_keywords:
            return 1.0

        return self.emotion_boost_factor


class TemporalVisualContext:
    """
    Temporal intelligence for vision memories
    Tracks when images were seen, accessed, and their recency
    Provides brain-like temporal awareness for visual memories
    """

    def __init__(self):
        # Memory ID → list of access timestamps
        self.access_history: Dict[str, List[float]] = defaultdict(list)
        print("⏰ TemporalVisualContext initialized")

    def record_access(self, memory_id: str, timestamp: float):
        """Record memory access for temporal tracking"""
        self.access_history[memory_id].append(timestamp)

        # Keep only recent accesses (last 100)
        if len(self.access_history[memory_id]) > 100:
            self.access_history[memory_id] = self.access_history[memory_id][-100:]

    def get_recent_access_count(self, memory_id: str, hours: float = 24) -> int:
        """Get number of accesses in last N hours"""
        if memory_id not in self.access_history:
            return 0

        cutoff_time = time.time() - (hours * 3600)
        recent_accesses = [t for t in self.access_history[memory_id] if t >= cutoff_time]

        return len(recent_accesses)

    def get_last_access_time(self, memory_id: str) -> Optional[float]:
        """Get timestamp of last access"""
        if memory_id not in self.access_history or not self.access_history[memory_id]:
            return None

        return max(self.access_history[memory_id])

    def get_temporal_boost(self, memory_id: str, current_time: float) -> float:
        """
        Calculate boost based on recent access patterns
        Recent + frequent = high boost

        Args:
            memory_id: Memory ID
            current_time: Current timestamp

        Returns: Temporal boost factor (1.0 = no boost, higher = more boost)
        """
        recent_count_24h = self.get_recent_access_count(memory_id, 24)
        recent_count_7d = self.get_recent_access_count(memory_id, 24 * 7)

        # Boost based on recent activity
        if recent_count_24h > 0:
            boost = 1.0 + (recent_count_24h * 0.1)  # +10% per access in last 24h
        elif recent_count_7d > 0:
            boost = 1.0 + (recent_count_7d * 0.05)  # +5% per access in last 7 days
        else:
            boost = 1.0

        return min(boost, 2.0)  # Cap at 2x


class ActiveVisionMemoryCore:
    """
    Main active memory orchestrator for vision RAG
    Coordinates asymptotic dynamics, emotion detection, temporal tracking
    Provides global entry points for retrieval and storage
    """

    def __init__(self, config_file: str = "Vision_RAG/vision_memory_config.json"):
        print("🧠 Initializing ActiveVisionMemoryCore...")

        # Load configuration
        self.config = self._load_config(config_file)

        # Load base RAG core
        self.base_rag = get_vision_rag_instance(config_file)

        # Initialize active components
        self.asymptotic_manager = AsymptoticMemoryManager(self.config)
        self.emotion_detector = EmotionKeywordDetector(self.config)
        self.temporal_context = TemporalVisualContext()

        # Configuration flags
        self.enable_emotion_boost = self.config['emotion_keywords']['enable_emotion_boost']
        self.enable_temporal_boost = self.config['asymptotic_dynamics']['timestamp_boost_enabled']
        self.enable_frequency_boost = self.config['asymptotic_dynamics']['frequency_boost_enabled']

        print("🎉 ActiveVisionMemoryCore initialization complete!")

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_file}")
            raise

    def process_vision_rag_input(self,
                                 query_image: Optional[Image.Image] = None,
                                 query_text: Optional[str] = None,
                                 active_mission_id: Optional[str] = None,
                                 max_memories: int = None) -> List[Dict[str, Any]]:
        """
        🧠 ENHANCED VISION RETRIEVAL (ALWAYS CALLED)

        Process:
        1. Retrieve candidate memories from base RAG
        2. Calculate current strength with all boosts
        3. Rank by final strength
        4. Update access counts and temporal tracking
        5. Return formatted results

        Args:
            query_image: Optional PIL Image for visual query
            query_text: Optional text for cross-modal query
            active_mission_id: Optional mission filter
            max_memories: Max results (default from config)

        Returns: List of {memory, similarity, final_strength, image_path, context_text, timestamp, reason}
        """
        if max_memories is None:
            max_memories = self.config['retrieval']['default_top_k']

        current_time = time.time()

        # Log retrieval
        query_type = "image" if query_image else "text"
        query_preview = query_text[:50] if query_text else "visual query"
        print(f"🔍 VISION RETRIEVAL: {query_type} query - '{query_preview}...'")

        # Retrieve from base RAG
        candidate_results = self.base_rag.retrieve_memories(
            query_image=query_image,
            query_text=query_text,
            top_k=max_memories * 2,  # Get more candidates for re-ranking
            mission_filter=active_mission_id
        )

        if not candidate_results:
            print("📝 No memories found matching query")
            return []

        # Calculate final strength for each result
        enhanced_results = []
        for result in candidate_results:
            memory = result['memory']
            base_similarity = result['similarity']

            # Calculate asymptotic strength
            asymptotic_strength = self.asymptotic_manager.calculate_memory_strength(
                memory, current_time
            )

            # Emotion boost (CHAT_MODE only)
            emotion_boost = self.emotion_detector.calculate_emotion_boost(
                memory.emotion_keywords,
                memory.mode
            )

            # Temporal boost (based on recent access patterns)
            temporal_boost = 1.0
            if self.enable_temporal_boost:
                temporal_boost = self.temporal_context.get_temporal_boost(
                    memory.id, current_time
                )

            # Combined final strength
            final_strength = base_similarity * asymptotic_strength * emotion_boost * temporal_boost

            enhanced_results.append({
                'memory': memory,
                'similarity': base_similarity,
                'asymptotic_strength': asymptotic_strength,
                'emotion_boost': emotion_boost,
                'temporal_boost': temporal_boost,
                'final_strength': final_strength,
                'image_path': memory.image_path,
                'context_text': memory.associated_text,
                'timestamp': memory.timestamp,
                'reason': memory.reason,
                'mode': memory.mode,
                'has_face': memory.has_face,
                'outcome': memory.outcome
            })

        # Sort by final strength
        enhanced_results.sort(key=lambda x: x['final_strength'], reverse=True)

        # Take top-k
        top_results = enhanced_results[:max_memories]

        # Update access counts and temporal tracking
        for result in top_results:
            memory = result['memory']
            memory.access_count += 1
            memory.last_access_time = current_time
            self.temporal_context.record_access(memory.id, current_time)

        # Log results
        print(f"✅ RETRIEVED {len(top_results)} vision memories:")
        for i, result in enumerate(top_results[:3], 1):  # Show top 3
            print(f"   {i}. Similarity: {result['similarity']:.3f}, "
                  f"Final: {result['final_strength']:.3f}, "
                  f"Mode: {result['mode']}, "
                  f"Reason: {result['reason']}")

        return top_results

    def update_vision_rag_memories(self,
                                   image: Image.Image,
                                   context_text: str,
                                   outcome: Optional[str] = None,
                                   mode: str = "CHAT_MODE",
                                   active_mission_id: Optional[str] = None) -> Optional[str]:
        """
        🧠 ENHANCED VISION STORAGE (ONLY WHEN IMAGE PRESENT)

        Process:
        1. Detect emotion keywords (CHAT_MODE only)
        2. Store via base RAG (gates will be checked there)
        3. Return memory ID or None if rejected

        Args:
            image: PIL Image to store
            context_text: Associated text context
            outcome: Optional outcome ("success", "failure", "error", "neutral")
            mode: "CHAT_MODE" or "ACTION_MODE"
            active_mission_id: Optional mission ID

        Returns: memory_id if stored, None if rejected by gates
        """
        print(f"💾 VISION STORAGE REQUEST: mode={mode}, outcome={outcome}")

        # Detect emotion keywords (CHAT_MODE only)
        emotion_keywords = []
        if mode == "CHAT_MODE" and self.enable_emotion_boost:
            emotion_keywords = self.emotion_detector.detect_keywords(context_text, mode)

        # Store via base RAG (gates applied there)
        memory_id = self.base_rag.store_memory(
            image=image,
            associated_text=context_text,
            outcome=outcome,
            mode=mode,
            emotion_keywords=emotion_keywords
        )

        if memory_id:
            # Log success
            emotion_str = f", emotions: {emotion_keywords}" if emotion_keywords else ""
            print(f"✅ VISION MEMORY STORED: {memory_id} (mode: {mode}{emotion_str})")

            # Associate with mission if provided
            if active_mission_id:
                memory = self.base_rag.memory_by_id.get(memory_id)
                if memory:
                    memory.associated_missions.append(active_mission_id)

        return memory_id

    def get_vision_memory_stats(self) -> Dict[str, Any]:
        """
        Enhanced memory statistics with active components

        Returns dict with:
        - Base stats from VisionRAGCore
        - Asymptotic dynamics info
        - Emotion keyword distribution
        - Temporal access patterns
        """
        # Get base stats
        base_stats = self.base_rag.get_memory_stats()

        # Add active memory stats
        active_stats = {
            'asymptotic_dynamics': {
                'storage_ceiling': self.asymptotic_manager.storage_ceiling,
                'decay_floor': self.asymptotic_manager.decay_floor,
                'decay_halflife_days': self.asymptotic_manager.decay_halflife_days,
                'max_frequency_boost': self.asymptotic_manager.max_frequency_boost
            },
            'emotion_keywords': {
                'enabled': self.enable_emotion_boost,
                'boost_factor': self.emotion_detector.emotion_boost_factor,
                'enabled_modes': self.emotion_detector.enabled_modes
            },
            'temporal_tracking': {
                'tracked_memories': len(self.temporal_context.access_history),
                'temporal_boost_enabled': self.enable_temporal_boost
            }
        }

        # Combine
        enhanced_stats = {**base_stats, **active_stats}

        return enhanced_stats

    def force_save(self):
        """Force save all vision memories and indices"""
        self.base_rag.force_save()
        print("💾 ACTIVE VISION MEMORY FORCE SAVE COMPLETE")


# ===== GLOBAL ENTRY POINTS =====
# These are the two main functions to be called from the main GUI
# Similar to TEXT RAG's process_input() and update_memory()

_active_vision_core: Optional[ActiveVisionMemoryCore] = None


def get_active_vision_instance(config_file: str = "Vision_RAG/vision_memory_config.json") -> ActiveVisionMemoryCore:
    """Get or create ActiveVisionMemoryCore singleton instance"""
    global _active_vision_core
    if _active_vision_core is None:
        _active_vision_core = ActiveVisionMemoryCore(config_file)
    return _active_vision_core


def process_vision_rag_input(query_image: Optional[Image.Image] = None,
                             query_text: Optional[str] = None,
                             active_mission_id: Optional[str] = None,
                             max_memories: int = None) -> List[Dict[str, Any]]:
    """
    🧠 GLOBAL ENTRY POINT 1: Vision RAG Retrieval

    ALWAYS called during prompt processing, even for text-only queries.
    Enables cross-modal retrieval: text query → find relevant images.

    Args:
        query_image: Optional PIL Image for visual query
        query_text: Optional text for cross-modal query
        active_mission_id: Optional mission filter
        max_memories: Max results (default from config)

    Returns: List of retrieved vision memories with metadata

    Example:
        # Text query finds relevant images
        results = process_vision_rag_input(query_text="show me elephants")

        # Image query finds similar images
        results = process_vision_rag_input(query_image=user_image)

        # Both
        results = process_vision_rag_input(query_image=img, query_text="my face")
    """
    active_vision = get_active_vision_instance()
    return active_vision.process_vision_rag_input(
        query_image=query_image,
        query_text=query_text,
        active_mission_id=active_mission_id,
        max_memories=max_memories
    )


def update_vision_rag_memories(image: Image.Image,
                               context_text: str,
                               outcome: Optional[str] = None,
                               mode: str = "CHAT_MODE",
                               active_mission_id: Optional[str] = None) -> Optional[str]:
    """
    🧠 GLOBAL ENTRY POINT 2: Vision RAG Storage

    ONLY called when image is present in the input.
    Applies storage gates, asymptotic compression, and emotion detection.

    Args:
        image: PIL Image to store
        context_text: Associated text context (user input + AI response)
        outcome: Optional outcome ("success", "failure", "error", "neutral")
        mode: "CHAT_MODE" or "ACTION_MODE"
        active_mission_id: Optional mission ID for association

    Returns: memory_id if stored (passed gates), None if rejected

    Example:
        # CHAT_MODE: User uploads photo
        memory_id = update_vision_rag_memories(
            image=user_photo,
            context_text="User: Here's my dog\nAI: Beautiful dog!",
            mode="CHAT_MODE"
        )

        # ACTION_MODE: Browser screenshot after success
        memory_id = update_vision_rag_memories(
            image=screenshot,
            context_text="Successfully clicked search button",
            outcome="success",
            mode="ACTION_MODE"
        )
    """
    active_vision = get_active_vision_instance()
    return active_vision.update_vision_rag_memories(
        image=image,
        context_text=context_text,
        outcome=outcome,
        mode=mode,
        active_mission_id=active_mission_id
    )


def get_vision_memory_stats() -> Dict[str, Any]:
    """
    🧠 GLOBAL FUNCTION: Get vision memory statistics

    Returns comprehensive stats including:
    - Total memories, mode breakdown, face count
    - Asymptotic dynamics parameters
    - Emotion keyword settings
    - Temporal tracking info
    """
    active_vision = get_active_vision_instance()
    return active_vision.get_vision_memory_stats()


def force_save_vision_memories():
    """
    💾 GLOBAL FUNCTION: Force save all vision memories and indices

    Call this before application shutdown or after major operations.
    """
    active_vision = get_active_vision_instance()
    active_vision.force_save()


# ===== TESTING =====
if __name__ == "__main__":
    print("🧪 Testing ActiveVisionMemoryCore...")

    # Initialize
    active_core = get_active_vision_instance()

    # Get stats
    stats = get_vision_memory_stats()
    print(f"\n📊 Stats:")
    print(json.dumps(stats, indent=2))

    print("\n✅ ActiveVisionMemoryCore module test complete!")
    print("\n📖 Usage:")
    print("   from Vision_RAG.vision_ragcore_activememory import process_vision_rag_input, update_vision_rag_memories")
    print("   results = process_vision_rag_input(query_text='show me my face')")
    print("   memory_id = update_vision_rag_memories(image, 'User uploaded photo', mode='CHAT_MODE')")
