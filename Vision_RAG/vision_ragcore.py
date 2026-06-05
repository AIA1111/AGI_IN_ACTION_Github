# vision_ragcore.py - Core Vision RAG Module
# Brain-like visual memory system with CLIP + FaceNet dual encoders
# Implements intelligent gating, asymptotic storage, and dual FAISS indices

import json
import os
import time
import hashlib
import pickle
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import numpy as np
from PIL import Image
import torch

# CLIP imports
from transformers import CLIPModel, CLIPProcessor

# Face recognition imports (via dlib - works on Apple Silicon)
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    print("⚠️ WARNING: face_recognition not installed. Face recognition will be disabled.")
    print("   Install with: pip install face_recognition")
    FACE_RECOGNITION_AVAILABLE = False

# FAISS imports
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    print("⚠️ WARNING: faiss not installed. Vector search will be disabled.")
    print("   Install with: pip install faiss-cpu")
    FAISS_AVAILABLE = False


@dataclass
class VisionMemoryItem:
    """
    Vision memory structure mirroring TEXT RAG's MemoryItem
    Stores both CLIP and face embeddings with comprehensive metadata
    """
    id: str                                  # Unique memory ID
    image_path: str                          # Path to stored image file
    clip_embedding: List[float]              # CLIP vector (512 dims)
    face_embedding: Optional[List[float]]    # face_recognition vector if face present (128 dims)
    has_face: bool                           # Face detection flag
    face_identity: Optional[str]             # "user", "ai_avatar", "unknown"

    # Context and tagging
    associated_text: str                     # Text context at time of storage
    reason: str                              # Why stored: "novelty", "success", "error", etc.
    outcome: Optional[str]                   # "success", "failure", "error", "neutral"
    mode: str                                # "CHAT_MODE" or "ACTION_MODE"

    # Temporal tracking
    timestamp: float                         # Unix timestamp
    last_access_time: float                  # Last retrieval time
    access_count: int = 0                    # Frequency tracking

    # Asymptotic strength
    stored_strength: float = 0.95            # Initial strength (≤ storage_ceiling)
    current_strength: float = 0.95           # Current strength after decay/boost

    # Mission linking (same as TEXT RAG)
    associated_missions: List[str] = field(default_factory=list)

    # Emotion keywords (CHAT_MODE only)
    emotion_keywords: List[str] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisionMemoryItem':
        """Create from dictionary"""
        return cls(**data)


class DualEncoder:
    """
    Dual-encoder system for visual memory
    - CLIP: General vision (scenes, objects, UI) - always used
    - face_recognition: Face identity (dlib-based, 128 dims) - used when face detected
    """

    def __init__(self, clip_model_path: str, config: Dict):
        print("🧠 Initializing DualEncoder (CLIP + face_recognition)...")

        self.config = config

        # Load CLIP model
        try:
            print(f"📥 Loading CLIP model from {clip_model_path}...")
            self.clip_model = CLIPModel.from_pretrained(clip_model_path)
            self.clip_processor = CLIPProcessor.from_pretrained(clip_model_path)

            # Move to GPU if available
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model.to(self.device)
            self.clip_model.eval()

            print(f"✅ CLIP model loaded successfully (device: {self.device})")
        except Exception as e:
            print(f"❌ FAILED to load CLIP model: {e}")
            raise

        # face_recognition configuration (dlib-based, no TensorFlow)
        self.face_enabled = FACE_RECOGNITION_AVAILABLE

        if self.face_enabled:
            print(f"✅ face_recognition enabled (dlib backend, 128-dim embeddings)")
        else:
            print("⚠️ face_recognition disabled (library not available)")

    def encode_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        Encode image with both CLIP and FaceNet (if face present)

        Returns:
        {
            'clip_embedding': np.ndarray (512 dims),
            'face_embedding': Optional[np.ndarray] (512 dims),
            'has_face': bool,
            'face_confidence': float
        }
        """
        result = {
            'clip_embedding': None,
            'face_embedding': None,
            'has_face': False,
            'face_confidence': 0.0
        }

        # CLIP encoding (always)
        try:
            with torch.no_grad():
                inputs = self.clip_processor(images=image, return_tensors="pt").to(self.device)
                clip_features = self.clip_model.get_image_features(**inputs)
                # Normalize for cosine similarity
                clip_embedding = clip_features / clip_features.norm(dim=-1, keepdim=True)
                result['clip_embedding'] = clip_embedding.cpu().numpy().flatten()
        except Exception as e:
            print(f"❌ CLIP encoding failed: {e}")
            raise

        # Face encoding using face_recognition (dlib-based)
        if self.face_enabled:
            try:
                # Convert PIL to numpy array (RGB format required)
                image_array = np.array(image)

                # Detect face locations
                face_locations = face_recognition.face_locations(image_array)

                if face_locations:
                    # Get face encodings (128-dimensional)
                    face_encodings = face_recognition.face_encodings(image_array, face_locations)

                    if face_encodings:
                        # Take first face if multiple detected
                        result['face_embedding'] = face_encodings[0]
                        result['has_face'] = True
                        result['face_confidence'] = 1.0  # face_recognition doesn't provide confidence

            except Exception as e:
                # Face detection failed or no face present - log for debugging
                print(f"⚠️ Face detection skipped: {e}")

        return result

    def encode_text(self, text: str) -> np.ndarray:
        """
        Encode text query with CLIP for cross-modal retrieval

        Returns: CLIP text embedding (512 dims)
        """
        try:
            with torch.no_grad():
                inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77).to(self.device)
                text_features = self.clip_model.get_text_features(**inputs)
                # Normalize for cosine similarity
                text_embedding = text_features / text_features.norm(dim=-1, keepdim=True)
                return text_embedding.cpu().numpy().flatten()
        except Exception as e:
            print(f"❌ CLIP text encoding failed: {e}")
            raise

    @staticmethod
    def calculate_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings
        Returns: Similarity score in [0, 1] range
        """
        # Ensure embeddings are normalized
        emb1_norm = emb1 / (np.linalg.norm(emb1) + 1e-8)
        emb2_norm = emb2 / (np.linalg.norm(emb2) + 1e-8)

        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)

        # Convert from [-1, 1] to [0, 1] range
        similarity = (similarity + 1.0) / 2.0

        return float(np.clip(similarity, 0.0, 1.0))


class StorageGates:
    """
    Intelligent gating to prevent memory explosion
    Only store images that pass at least one gate
    Mirrors brain's selective attention and consolidation
    """

    def __init__(self, config: Dict):
        self.novelty_threshold = config['storage_gates']['novelty_gate_threshold']
        self.outcome_gate_enabled = config['storage_gates']['enable_outcome_gate']
        self.decision_gate_enabled = config['storage_gates']['enable_decision_gate']
        self.attention_gate_enabled = config['storage_gates']['enable_attention_gate']
        self.recent_window = config['storage_gates']['recent_memory_window']

        # Decision keywords (agent behavior change)
        self.decision_keywords = [
            'changed approach', 'tried different', 'switched to', 'instead of',
            'alternative', 'retry', 'different method', 'new strategy'
        ]

        # Attention keywords (explicit visual reference)
        self.attention_keywords = [
            'i see', 'visible', 'the button', 'the dialog', 'the window',
            'screenshot', 'image shows', 'displayed', 'on screen', 'appears'
        ]

        print(f"🚪 StorageGates initialized (novelty threshold: {self.novelty_threshold})")

    def passes_novelty_gate(self, new_embedding: np.ndarray,
                           recent_embeddings: List[np.ndarray]) -> bool:
        """
        Gate 1: Novelty - only store if sufficiently different from recent memories
        Returns True if max similarity < threshold

        Example: 0.92 threshold means only store if <92% similar to recent images
        """
        if not recent_embeddings:
            return True  # Always pass if no recent memories

        # Calculate similarity to all recent memories
        similarities = [
            DualEncoder.calculate_similarity(new_embedding, recent_emb)
            for recent_emb in recent_embeddings
        ]

        max_similarity = max(similarities) if similarities else 0.0

        passes = max_similarity < self.novelty_threshold

        if not passes:
            print(f"🚫 NOVELTY GATE: Rejected (max similarity: {max_similarity:.3f} >= {self.novelty_threshold})")

        return passes

    def passes_outcome_gate(self, outcome: Optional[str]) -> bool:
        """
        Gate 2: Outcome - store if led to success/failure/error/correction
        Returns True if outcome is significant
        """
        if not self.outcome_gate_enabled:
            return False

        if outcome is None:
            return False

        significant_outcomes = ['success', 'failure', 'error', 'correction']
        passes = outcome.lower() in significant_outcomes

        if passes:
            print(f"✅ OUTCOME GATE: Passed (outcome: {outcome})")

        return passes

    def passes_decision_gate(self, context_text: str) -> bool:
        """
        Gate 3: Decision - store if agent changed behavior
        Detects phrases indicating behavioral changes
        """
        if not self.decision_gate_enabled:
            return False

        text_lower = context_text.lower()

        for keyword in self.decision_keywords:
            if keyword in text_lower:
                print(f"✅ DECISION GATE: Passed (detected: '{keyword}')")
                return True

        return False

    def passes_attention_gate(self, context_text: str) -> bool:
        """
        Gate 4: Attention - store if model explicitly referenced visual element
        Detects visual attention in the conversation
        """
        if not self.attention_gate_enabled:
            return False

        text_lower = context_text.lower()

        for keyword in self.attention_keywords:
            if keyword in text_lower:
                print(f"✅ ATTENTION GATE: Passed (detected: '{keyword}')")
                return True

        return False

    def should_store(self, new_embedding: np.ndarray,
                     recent_embeddings: List[np.ndarray],
                     outcome: Optional[str],
                     context_text: str) -> Tuple[bool, str]:
        """
        Check all gates and return (should_store, reason)

        Returns:
        - (True, "novelty") if passes novelty gate
        - (True, "outcome_success") if passes outcome gate
        - (True, "decision") if passes decision gate
        - (True, "attention") if passes attention gate
        - (False, "no_gate_passed") if fails all gates
        """
        # Check novelty gate first (most important)
        if self.passes_novelty_gate(new_embedding, recent_embeddings):
            return True, "novelty"

        # Check outcome gate
        if self.passes_outcome_gate(outcome):
            return True, f"outcome_{outcome}"

        # Check decision gate
        if self.passes_decision_gate(context_text):
            return True, "decision"

        # Check attention gate
        if self.passes_attention_gate(context_text):
            return True, "attention"

        # No gate passed
        return False, "no_gate_passed"


class VisionRAGCore:
    """
    Core VISION RAG system managing dual indices and memory lifecycle
    Brain-like visual memory with selective attention and consolidation
    """

    def __init__(self, config_file: str = "Vision_RAG/vision_memory_config.json"):
        print("🧠 Initializing VisionRAGCore...")

        # Load configuration
        self.config = self._load_config(config_file)
        self.config_file = config_file

        # Initialize dual encoder
        self.dual_encoder = DualEncoder(
            self.config['clip_model_path'],
            self.config
        )

        # Initialize storage gates
        self.storage_gates = StorageGates(self.config)

        # Memory storage
        self.memories: List[VisionMemoryItem] = []
        self.memory_by_id: Dict[str, VisionMemoryItem] = {}

        # FAISS indices
        self.clip_index = None
        self.face_index = None
        self.clip_dimension = 768  # CLIP ViT-Large-Patch14 output dimension
        self.face_dimension = 128  # face_recognition output dimension

        # Ensure required directories exist
        os.makedirs("Vision_RAG/faiss_index", exist_ok=True)
        os.makedirs(self.config['image_storage']['chat_mode_dir'], exist_ok=True)
        os.makedirs(self.config['image_storage']['action_mode_dir'], exist_ok=True)

        # Load existing memories and indices
        self._load_memories()
        self._load_or_create_indices()

        # Auto-save counter
        self.save_counter = 0
        self.auto_save_interval = self.config['memory_storage']['auto_save_interval']

        print(f"🎉 VisionRAGCore initialized successfully!")
        print(f"📊 Current stats: {len(self.memories)} memories loaded")

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"✅ Configuration loaded from {config_file}")
            return config
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {config_file}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in configuration file: {e}")
            raise

    def _load_memories(self):
        """Load existing memories from JSON file"""
        metadata_file = self.config['memory_storage']['metadata_file']

        if not os.path.exists(metadata_file):
            print(f"📝 No existing memories found (will create new file)")
            return

        try:
            with open(metadata_file, 'r') as f:
                memories_data = json.load(f)

            for mem_data in memories_data:
                memory = VisionMemoryItem.from_dict(mem_data)
                self.memories.append(memory)
                self.memory_by_id[memory.id] = memory

            print(f"✅ Loaded {len(self.memories)} existing memories from {metadata_file}")

        except Exception as e:
            print(f"❌ Failed to load memories: {e}")
            print(f"⚠️ Starting with empty memory")

    def _save_memories(self):
        """Save memories to JSON file"""
        metadata_file = self.config['memory_storage']['metadata_file']

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(metadata_file), exist_ok=True)

            # Convert memories to dict
            memories_data = [mem.to_dict() for mem in self.memories]

            # Save to file
            with open(metadata_file, 'w') as f:
                json.dump(memories_data, f, indent=2)

            print(f"💾 Saved {len(self.memories)} memories to {metadata_file}")

        except Exception as e:
            print(f"❌ Failed to save memories: {e}")

    def _load_or_create_indices(self):
        """Load existing FAISS indices or create new ones"""
        if not FAISS_AVAILABLE:
            print("⚠️ FAISS not available - vector search disabled")
            return

        clip_index_path = self.config['faiss_index']['clip_index_path']
        clip_metadata_path = self.config['faiss_index']['clip_metadata_path']
        face_index_path = self.config['faiss_index']['face_index_path']
        face_metadata_path = self.config['faiss_index']['face_metadata_path']

        # Create CLIP index
        if os.path.exists(clip_index_path) and os.path.exists(clip_metadata_path):
            try:
                self.clip_index = faiss.read_index(clip_index_path)
                with open(clip_metadata_path, 'rb') as f:
                    clip_metadata = pickle.load(f)
                print(f"✅ Loaded CLIP index ({self.clip_index.ntotal} vectors)")
            except Exception as e:
                print(f"⚠️ Failed to load CLIP index: {e}")
                self._create_clip_index()
                self._rebuild_indices_from_memories()
        else:
            self._create_clip_index()
            # If memories exist but index doesn't, rebuild from existing memories
            if len(self.memories) > 0:
                print(f"⚠️  Found {len(self.memories)} existing memories but no index - rebuilding...")
                self._rebuild_indices_from_memories()

        # Create Face index
        if os.path.exists(face_index_path) and os.path.exists(face_metadata_path):
            try:
                self.face_index = faiss.read_index(face_index_path)
                with open(face_metadata_path, 'rb') as f:
                    face_metadata = pickle.load(f)
                print(f"✅ Loaded Face index ({self.face_index.ntotal} vectors)")
            except Exception as e:
                print(f"⚠️ Failed to load Face index: {e}")
                self._create_face_index()
        else:
            self._create_face_index()

    def _create_clip_index(self):
        """Create new CLIP FAISS index"""
        if not FAISS_AVAILABLE:
            return

        self.clip_index = faiss.IndexFlatIP(self.clip_dimension)  # Inner product for cosine similarity
        print(f"✅ Created new CLIP index (dimension: {self.clip_dimension})")

    def _create_face_index(self):
        """Create new FAISS index for face embeddings (face_recognition, 128 dims)"""
        if not FAISS_AVAILABLE:
            return

        self.face_index = faiss.IndexFlatIP(self.face_dimension)
        print(f"✅ Created new Face index (dimension: {self.face_dimension})")

    def _rebuild_indices_from_memories(self):
        """Rebuild FAISS indices from existing memory images"""
        if not FAISS_AVAILABLE or len(self.memories) == 0:
            return

        print(f"🔄 Rebuilding indices from {len(self.memories)} existing memories...")

        rebuilt_count = 0
        for memory in self.memories:
            try:
                # Load image from disk
                image = Image.open(memory.image_path)

                # Re-encode with CLIP
                encodings = self.dual_encoder.encode_image(image)

                # Add to CLIP index
                clip_vector = np.array([encodings['clip_embedding']], dtype=np.float32)
                faiss.normalize_L2(clip_vector)
                self.clip_index.add(clip_vector)

                # Add to Face index if face present
                if encodings['has_face'] and encodings['face_embedding'] is not None:
                    face_vector = np.array([encodings['face_embedding']], dtype=np.float32)
                    faiss.normalize_L2(face_vector)
                    self.face_index.add(face_vector)

                rebuilt_count += 1

            except Exception as e:
                print(f"⚠️  Failed to rebuild index for {memory.id}: {e}")
                continue

        print(f"✅ Rebuilt indices: {rebuilt_count}/{len(self.memories)} memories")
        print(f"   CLIP index: {self.clip_index.ntotal} vectors")
        print(f"   Face index: {self.face_index.ntotal if self.face_index else 0} vectors")

        # Save rebuilt indices
        self._save_indices()

    def _save_indices(self):
        """Save FAISS indices to disk"""
        if not FAISS_AVAILABLE or self.clip_index is None:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config['faiss_index']['clip_index_path']), exist_ok=True)

            # Save CLIP index
            faiss.write_index(self.clip_index, self.config['faiss_index']['clip_index_path'])

            # Save CLIP metadata (memory IDs in order)
            clip_metadata = [mem.id for mem in self.memories]
            with open(self.config['faiss_index']['clip_metadata_path'], 'wb') as f:
                pickle.dump(clip_metadata, f)

            # Save Face index
            if self.face_index is not None:
                faiss.write_index(self.face_index, self.config['faiss_index']['face_index_path'])

                # Save Face metadata (only memories with faces)
                face_metadata = [mem.id for mem in self.memories if mem.has_face]
                with open(self.config['faiss_index']['face_metadata_path'], 'wb') as f:
                    pickle.dump(face_metadata, f)

            print(f"💾 FAISS indices saved successfully")

        except Exception as e:
            print(f"❌ Failed to save FAISS indices: {e}")

    def _generate_memory_id(self) -> str:
        """Generate unique memory ID"""
        timestamp = int(time.time() * 1000)  # Milliseconds
        random_hash = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        return f"vis_{timestamp}_{random_hash}"

    def _save_image_file(self, image: Image.Image, memory_id: str, mode: str) -> str:
        """
        Save image to disk and return file path

        Args:
            image: PIL Image
            memory_id: Unique memory ID
            mode: "CHAT_MODE" or "ACTION_MODE"

        Returns: Relative path to saved image
        """
        # Determine directory based on mode
        # Accept both old names (CHAT_MODE/ACTION_MODE) and new names (USER_CHAT/AUTO_PROCESS)
        if mode in ["CHAT_MODE", "USER_CHAT"]:
            save_dir = self.config['image_storage']['chat_mode_dir']
        else:
            save_dir = self.config['image_storage']['action_mode_dir']

        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp_str = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"{timestamp_str}_{memory_id}.{self.config['image_storage']['image_format']}"
        filepath = os.path.join(save_dir, filename)

        # Resize if needed
        max_resolution = self.config['image_storage']['max_resolution']
        if image.width > max_resolution[0] or image.height > max_resolution[1]:
            image.thumbnail(max_resolution, Image.Resampling.LANCZOS)

        # Save image (convert jpg -> jpeg for PIL compatibility)
        image_format = self.config['image_storage']['image_format'].upper()
        if image_format == 'JPG':
            image_format = 'JPEG'

        image.save(
            filepath,
            format=image_format,
            quality=self.config['image_storage']['image_quality']
        )

        return filepath

    def _get_recent_embeddings(self, count: int) -> List[np.ndarray]:
        """Get CLIP embeddings of N most recent memories for novelty gate"""
        if not self.memories:
            return []

        # Sort by timestamp (most recent first)
        recent_memories = sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:count]

        # Extract CLIP embeddings
        embeddings = [np.array(mem.clip_embedding) for mem in recent_memories]

        return embeddings

    def store_memory(self,
                    image: Image.Image,
                    associated_text: str,
                    outcome: Optional[str] = None,
                    mode: str = "CHAT_MODE",
                    emotion_keywords: Optional[List[str]] = None) -> Optional[str]:
        """
        Store image memory if passes storage gates

        Process:
        1. Encode image (CLIP + FaceNet if face present)
        2. Check storage gates
        3. If passes, apply storage ceiling (asymptotic compression)
        4. Save image file
        5. Add to FAISS indices
        6. Save metadata
        7. Auto-save periodically

        Args:
            image: PIL Image to store
            associated_text: Context text at time of storage
            outcome: Optional outcome ("success", "failure", "error", "neutral")
            mode: "CHAT_MODE" or "ACTION_MODE"
            emotion_keywords: Pre-detected emotion keywords (from active layer)

        Returns: memory_id if stored, None if rejected by gates
        """
        # Encode image
        encodings = self.dual_encoder.encode_image(image)

        # Get recent embeddings for novelty gate
        recent_embeddings = self._get_recent_embeddings(
            self.config['storage_gates']['recent_memory_window']
        )

        # Check storage gates based on memory type (tag in associated_text)
        # "User instructed vision memory" → Bypass gates (store everything, supervised learning)
        # "Auto generated vision memory" → Use gates (filter redundant screenshots)
        is_user_instructed = "User instructed vision memory" in associated_text
        is_auto_generated = "Auto generated vision memory" in associated_text

        if is_user_instructed or mode == "USER_CHAT":
            # User chatting with AI - bypass gates (like TEXT RAG with [USER] tag)
            should_store = True
            reason = "user_instructed_supervised_learning"
            print(f"✅ USER INSTRUCTED: Bypassing gates (supervised learning - store everything)")
        elif is_auto_generated or mode == "AUTO_PROCESS":
            # Automated processes (screen recording, scheduled agents) - novelty gate MANDATORY
            # Check novelty gate first
            passes_novelty = self.storage_gates.passes_novelty_gate(
                encodings['clip_embedding'],
                recent_embeddings
            )

            if passes_novelty:
                # Novelty passed - store it
                should_store = True
                reason = "novelty"
                print(f"✅ AUTO PROCESS: Passed novelty gate (sufficiently different)")
            else:
                # Novelty failed - check other gates as fallback (outcome, decision)
                # NOTE: Attention gate skipped to prevent "screenshot" keyword false positives
                if self.storage_gates.passes_outcome_gate(outcome):
                    should_store = True
                    reason = f"outcome_{outcome}"
                    print(f"✅ AUTO PROCESS: Novelty failed but outcome gate passed - {reason}")
                elif self.storage_gates.passes_decision_gate(associated_text):
                    should_store = True
                    reason = "decision"
                    print(f"✅ AUTO PROCESS: Novelty failed but decision gate passed")
                else:
                    # All gates failed
                    should_store = False
                    reason = "no_gate_passed"
                    print(f"🚫 AUTO PROCESS: Rejected - novelty failed, no other gates passed")
        else:
            # Default: use gates for backward compatibility
            should_store, reason = self.storage_gates.should_store(
                encodings['clip_embedding'],
                recent_embeddings,
                outcome,
                associated_text
            )

        if not should_store:
            print(f"🚫 STORAGE REJECTED: {reason}")
            return None

        # Gates passed - proceed with storage
        print(f"✅ STORAGE APPROVED: {reason}")

        # Generate memory ID
        memory_id = self._generate_memory_id()

        # Save image file
        image_path = self._save_image_file(image, memory_id, mode)

        # Apply storage ceiling (asymptotic compression)
        storage_ceiling = self.config['storage']['storage_ceiling']
        # Base strength is 1.0 for perfect novelty, reduced by ceiling
        stored_strength = 1.0 * storage_ceiling  # Will be 0.95 by default

        # Create memory item
        memory = VisionMemoryItem(
            id=memory_id,
            image_path=image_path,
            clip_embedding=encodings['clip_embedding'].tolist(),
            face_embedding=encodings['face_embedding'].tolist() if encodings['face_embedding'] is not None else None,
            has_face=encodings['has_face'],
            face_identity="unknown" if encodings['has_face'] else None,  # Will be labeled later
            associated_text=associated_text,
            reason=reason,
            outcome=outcome,
            mode=mode,
            timestamp=time.time(),
            last_access_time=time.time(),
            access_count=0,
            stored_strength=stored_strength,
            current_strength=stored_strength,
            emotion_keywords=emotion_keywords or [],
            tags=[],
            metadata={}
        )

        # Add to memory list
        self.memories.append(memory)
        self.memory_by_id[memory_id] = memory

        # Add to FAISS indices
        if FAISS_AVAILABLE:
            # Add to CLIP index
            clip_vector = np.array([encodings['clip_embedding']], dtype=np.float32)
            self.clip_index.add(clip_vector)

            # Add to Face index if face present
            if encodings['has_face'] and encodings['face_embedding'] is not None:
                face_vector = np.array([encodings['face_embedding']], dtype=np.float32)
                self.face_index.add(face_vector)

        # Auto-save periodically
        self.save_counter += 1
        if self.save_counter >= self.auto_save_interval:
            self._save_memories()
            self._save_indices()
            self.save_counter = 0

        print(f"💾 STORED MEMORY: {memory_id} (mode: {mode}, has_face: {encodings['has_face']}, reason: {reason})")

        return memory_id

    def retrieve_memories(self,
                         query_image: Optional[Image.Image] = None,
                         query_text: Optional[str] = None,
                         top_k: int = None,
                         mode_filter: Optional[str] = None,
                         mission_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve memories based on image or text query

        Process:
        1. Encode query (image → CLIP+Face, text → CLIP text encoder)
        2. If query has face → prioritize face index
        3. Search FAISS indices
        4. Filter by mode if specified
        5. Return top-k with metadata
        6. Update access counts (done in active layer)

        Args:
            query_image: Optional PIL Image for visual query
            query_text: Optional text for cross-modal query
            top_k: Number of results (default from config)
            mode_filter: Filter by "CHAT_MODE" or "ACTION_MODE"
            mission_filter: Filter by mission ID

        Returns: List of dicts with {memory, similarity, source}
        """
        if not FAISS_AVAILABLE or self.clip_index is None:
            print("⚠️ FAISS not available - cannot retrieve memories")
            return []

        if not self.memories:
            print("📝 No memories stored yet")
            return []

        if query_image is None and query_text is None:
            print("❌ RETRIEVAL ERROR: Must provide either query_image or query_text")
            return []

        if top_k is None:
            top_k = self.config['retrieval']['default_top_k']

        # Encode query
        if query_image is not None:
            # Visual query
            encodings = self.dual_encoder.encode_image(query_image)
            query_clip_emb = encodings['clip_embedding']
            query_face_emb = encodings['face_embedding']
            has_face_query = encodings['has_face']
        else:
            # Text query
            query_clip_emb = self.dual_encoder.encode_text(query_text)
            query_face_emb = None
            has_face_query = False

        results = []

        # Strategy: Prioritize face matches if query has face
        if has_face_query and query_face_emb is not None and self.face_index is not None:
            print(f"🔍 RETRIEVAL: Face-priority search (query has face)")

            # Search face index
            face_results = self._search_face_index(query_face_emb, top_k=top_k)

            # Also search CLIP index for context
            clip_results = self._search_clip_index(query_clip_emb, top_k=top_k)

            # Merge with weights (70% face, 30% CLIP)
            results = self._merge_results(
                face_results,
                clip_results,
                face_weight=self.config['retrieval']['face_priority_weight'],
                clip_weight=self.config['retrieval']['clip_context_weight']
            )

        else:
            # CLIP-only search
            print(f"🔍 RETRIEVAL: CLIP search ({'text query' if query_text else 'image without face'})")
            results = self._search_clip_index(query_clip_emb, top_k=top_k)

        # Apply filters
        if mode_filter:
            results = [r for r in results if r['memory'].mode == mode_filter]

        if mission_filter:
            results = [r for r in results if mission_filter in r['memory'].associated_missions]

        # Limit to top_k
        results = results[:top_k]

        print(f"✅ RETRIEVED {len(results)} memories")

        return results

    def _search_clip_index(self, query_embedding: np.ndarray, top_k: int) -> List[Dict[str, Any]]:
        """Search CLIP FAISS index and return results"""
        if self.clip_index is None or self.clip_index.ntotal == 0:
            return []

        # Prepare query vector (needs to be 2D array)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Search
        k = min(top_k * 2, self.clip_index.ntotal)  # Get more candidates for filtering
        distances, indices = self.clip_index.search(query_vector, k)

        # Convert to results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.memories):
                memory = self.memories[idx]
                # Convert inner product distance to similarity [0, 1]
                similarity = (distance + 1.0) / 2.0
                results.append({
                    'memory': memory,
                    'similarity': float(similarity),
                    'source': 'clip'
                })

        return results

    def _search_face_index(self, query_embedding: np.ndarray, top_k: int) -> List[Dict[str, Any]]:
        """Search Face FAISS index and return results"""
        if self.face_index is None or self.face_index.ntotal == 0:
            return []

        # Prepare query vector
        query_vector = np.array([query_embedding], dtype=np.float32)

        # Search
        k = min(top_k, self.face_index.ntotal)
        distances, indices = self.face_index.search(query_vector, k)

        # Convert to results
        # Need to map face index positions to memory indices
        face_memories = [mem for mem in self.memories if mem.has_face]

        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(face_memories):
                memory = face_memories[idx]
                similarity = (distance + 1.0) / 2.0
                results.append({
                    'memory': memory,
                    'similarity': float(similarity),
                    'source': 'face'
                })

        return results

    def _merge_results(self,
                      face_results: List[Dict],
                      clip_results: List[Dict],
                      face_weight: float,
                      clip_weight: float) -> List[Dict]:
        """
        Merge face and CLIP results with weighted scoring

        Args:
            face_results: Results from face index
            clip_results: Results from CLIP index
            face_weight: Weight for face similarity (e.g., 0.7)
            clip_weight: Weight for CLIP similarity (e.g., 0.3)

        Returns: Merged and sorted results
        """
        # Create combined scores
        memory_scores = {}

        # Add face results
        for result in face_results:
            mem_id = result['memory'].id
            memory_scores[mem_id] = {
                'memory': result['memory'],
                'face_similarity': result['similarity'],
                'clip_similarity': 0.0,
                'source': 'face'
            }

        # Add/update with CLIP results
        for result in clip_results:
            mem_id = result['memory'].id
            if mem_id in memory_scores:
                memory_scores[mem_id]['clip_similarity'] = result['similarity']
                memory_scores[mem_id]['source'] = 'both'
            else:
                memory_scores[mem_id] = {
                    'memory': result['memory'],
                    'face_similarity': 0.0,
                    'clip_similarity': result['similarity'],
                    'source': 'clip'
                }

        # Calculate combined scores
        combined_results = []
        for mem_id, scores in memory_scores.items():
            combined_score = (
                scores['face_similarity'] * face_weight +
                scores['clip_similarity'] * clip_weight
            )
            combined_results.append({
                'memory': scores['memory'],
                'similarity': combined_score,
                'source': scores['source']
            })

        # Sort by combined score
        combined_results.sort(key=lambda x: x['similarity'], reverse=True)

        return combined_results

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Return comprehensive memory statistics

        Returns dict with:
        - total_memories
        - chat_mode_count
        - action_mode_count
        - memories_with_faces
        - avg_access_count
        - oldest_memory_age_days
        - newest_memory_age_days
        """
        if not self.memories:
            return {
                'total_memories': 0,
                'chat_mode_count': 0,
                'action_mode_count': 0,
                'memories_with_faces': 0,
                'avg_access_count': 0.0,
                'oldest_memory_age_days': 0.0,
                'newest_memory_age_days': 0.0
            }

        current_time = time.time()

        chat_count = sum(1 for m in self.memories if m.mode == "CHAT_MODE")
        action_count = sum(1 for m in self.memories if m.mode == "ACTION_MODE")
        face_count = sum(1 for m in self.memories if m.has_face)

        access_counts = [m.access_count for m in self.memories]
        avg_access = sum(access_counts) / len(access_counts) if access_counts else 0.0

        timestamps = [m.timestamp for m in self.memories]
        oldest_age = (current_time - min(timestamps)) / 86400 if timestamps else 0.0  # Days
        newest_age = (current_time - max(timestamps)) / 86400 if timestamps else 0.0

        return {
            'total_memories': len(self.memories),
            'chat_mode_count': chat_count,
            'action_mode_count': action_count,
            'memories_with_faces': face_count,
            'avg_access_count': avg_access,
            'oldest_memory_age_days': oldest_age,
            'newest_memory_age_days': newest_age,
            'clip_index_size': self.clip_index.ntotal if self.clip_index else 0,
            'face_index_size': self.face_index.ntotal if self.face_index else 0
        }

    def force_save(self):
        """Force save memories and indices"""
        self._save_memories()
        self._save_indices()
        print("💾 FORCE SAVE COMPLETE")


# Singleton instance (similar to TEXT RAG pattern)
_vision_rag_core_instance: Optional[VisionRAGCore] = None


def get_vision_rag_instance(config_file: str = "Vision_RAG/vision_memory_config.json") -> VisionRAGCore:
    """Get or create VisionRAGCore singleton instance"""
    global _vision_rag_core_instance
    if _vision_rag_core_instance is None:
        _vision_rag_core_instance = VisionRAGCore(config_file)
    return _vision_rag_core_instance


# Test function
if __name__ == "__main__":
    print("🧪 Testing VisionRAGCore...")

    # Initialize
    rag = get_vision_rag_instance()

    # Print stats
    stats = rag.get_memory_stats()
    print(f"\n📊 Stats: {stats}")

    print("\n✅ VisionRAGCore module test complete!")
