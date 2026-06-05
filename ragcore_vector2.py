# ragcore_vector2.py - Enhanced RAG Module with Mission-Persistent Context
# Universal learning system with human-brain-like memory and goal awareness

import hashlib
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
import os
import re
from datetime import datetime, timedelta


@dataclass
class MemoryItem:
    """Enhanced memory structure with versioning and knowledge lineage"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    timestamp: float
    tags: List[str]

    # Knowledge evolution tracking - this is what makes it brain-like
    superseded_by: Optional[str] = None  # ID of memory that replaces this one
    supersedes: Optional[str] = None  # ID of memory this one replaces
    version: int = 1  # Version number for knowledge evolution
    confidence_score: float = 5.0  # How confident we are in this knowledge

    # Mission context integration
    associated_missions: List[str] = field(default_factory=list)  # Mission IDs this memory relates to
    mission_relevance_scores: Dict[str, float] = field(default_factory=dict)  # Relevance to specific missions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
            "version": self.version,
            "confidence_score": self.confidence_score,
            "associated_missions": self.associated_missions,
            "mission_relevance_scores": self.mission_relevance_scores
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data["embedding"],
            metadata=data["metadata"],
            timestamp=data["timestamp"],
            tags=data["tags"],
            superseded_by=data.get("superseded_by"),
            supersedes=data.get("supersedes"),
            version=data.get("version", 1),
            confidence_score=data.get("confidence_score", 5.0),
            associated_missions=data.get("associated_missions", []),
            mission_relevance_scores=data.get("mission_relevance_scores", {})
        )


@dataclass
class Mission:
    """Represents an active, persistent goal or task - mirrors human goal-oriented thinking"""
    id: str
    title: str
    description: str
    start_time: float
    status: str  # "active", "paused", "completed", "cancelled"
    priority: int  # 1-10, higher means more important

    # Mission-specific knowledge accumulation - like working memory for a specific goal
    key_findings: List[Dict[str, Any]] = field(default_factory=list)  # Critical discoveries with metadata
    current_focus: str = ""  # What aspect we're currently working on
    next_steps: List[str] = field(default_factory=list)  # Planned actions
    obstacles: List[str] = field(default_factory=list)  # Known challenges or blockers
    successful_strategies: List[str] = field(default_factory=list)  # What's working well

    # Context management for intelligent retrieval
    relevant_domains: List[str] = field(default_factory=list)  # Which knowledge domains are relevant
    context_keywords: List[str] = field(default_factory=list)  # Key terms for memory retrieval
    related_missions: List[str] = field(default_factory=list)  # Other missions that connect to this one

    # Learning and adaptation tracking
    completion_criteria: List[str] = field(default_factory=list)  # What defines success
    last_activity_time: float = field(default_factory=lambda: time.time())
    total_interactions: int = 0
    progress_indicators: Dict[str, float] = field(default_factory=dict)  # Measurable progress metrics

    def add_key_finding(self, finding: str, importance: float = 5.0, source: str = "conversation"):
        """Add a key finding with metadata - like forming important memories during goal pursuit"""
        finding_entry = {
            "content": finding,
            "timestamp": time.time(),
            "importance": importance,
            "source": source,
            "access_count": 0
        }
        self.key_findings.append(finding_entry)

        # Keep only the most important findings to prevent context bloat
        if len(self.key_findings) > 15:
            self.key_findings.sort(key=lambda x: (x["importance"], x["access_count"]), reverse=True)
            self.key_findings = self.key_findings[:12]  # Keep top 12, room to grow

    def is_relevant_to_query(self, query: str) -> float:
        """Calculate how relevant this mission is to the current query - like attention filtering"""
        query_lower = query.lower()
        relevance_score = 0.0

        # Check title and description relevance
        title_words = set(self.title.lower().split())
        desc_words = set(self.description.lower().split())
        query_words = set(query_lower.split())

        title_overlap = len(title_words.intersection(query_words)) / max(len(title_words), 1)
        desc_overlap = len(desc_words.intersection(query_words)) / max(len(desc_words), 1)

        relevance_score += title_overlap * 0.4 + desc_overlap * 0.3

        # Check context keywords
        if self.context_keywords:
            keyword_matches = sum(1 for kw in self.context_keywords if kw.lower() in query_lower)
            relevance_score += (keyword_matches / len(self.context_keywords)) * 0.3

        return min(relevance_score, 1.0)

    def update_activity(self):
        """Update last activity time and interaction count - tracks engagement with mission"""
        self.last_activity_time = time.time()
        self.total_interactions += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "status": self.status,
            "priority": self.priority,
            "key_findings": self.key_findings,
            "current_focus": self.current_focus,
            "next_steps": self.next_steps,
            "obstacles": self.obstacles,
            "successful_strategies": self.successful_strategies,
            "relevant_domains": self.relevant_domains,
            "context_keywords": self.context_keywords,
            "related_missions": self.related_missions,
            "completion_criteria": self.completion_criteria,
            "last_activity_time": self.last_activity_time,
            "total_interactions": self.total_interactions,
            "progress_indicators": self.progress_indicators
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Mission':
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            start_time=data["start_time"],
            status=data["status"],
            priority=data["priority"],
            key_findings=data.get("key_findings", []),
            current_focus=data.get("current_focus", ""),
            next_steps=data.get("next_steps", []),
            obstacles=data.get("obstacles", []),
            successful_strategies=data.get("successful_strategies", []),
            relevant_domains=data.get("relevant_domains", []),
            context_keywords=data.get("context_keywords", []),
            related_missions=data.get("related_missions", []),
            completion_criteria=data.get("completion_criteria", []),
            last_activity_time=data.get("last_activity_time", time.time()),
            total_interactions=data.get("total_interactions", 0),
            progress_indicators=data.get("progress_indicators", {})
        )


class MemoryConfig:
    """Configuration management for memory system with mission support"""

    def __init__(self, config_file="memory_config.json"):
        self.config_file = config_file
        self.default_config = {
            "max_total_memories": 10000,
            "tier1_max_percentage": 30,
            "tier2_max_percentage": 50,
            "tier3_percentage": 20,
            "auto_save_interval": 1,
            "enable_knowledge_evolution": True,
            "confidence_threshold_override": 8.0,
            "domain_adaptation": True,
            "tier1_evolution_threshold": 9.0,
            "tier2_evolution_threshold": 7.0,
            "tier3_evolution_threshold": 5.0,

            # Mission-specific configuration
            "max_active_missions": 15,  # Maximum concurrent missions
            "mission_auto_pause_days": 30,  # Auto-pause missions after 30 days of inactivity
            "mission_relevance_threshold": 0.3,  # Minimum relevance to include mission context
            "max_mission_context_findings": 5  # Maximum findings per mission in context
        }
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file, create with defaults if not exists"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                config = self.default_config.copy()
                config.update(loaded_config)
                return config
            else:
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            print(f"Config load error: {e}, using defaults")
            return self.default_config.copy()

    def save_config(self, config: Dict[str, Any] = None):
        """Save current configuration to file"""
        try:
            config_to_save = config or self.config
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def update_max_memories(self, new_max: int):
        """Update maximum memory count and save immediately"""
        self.config["max_total_memories"] = new_max
        self.save_config()

    def get_tier_limits(self) -> Tuple[int, int, int]:
        """Calculate memory limits for each tier based on percentages"""
        total = self.config["max_total_memories"]
        tier1_max = int(total * self.config["tier1_max_percentage"] / 100)
        tier2_max = int(total * self.config["tier2_max_percentage"] / 100)
        tier3_max = total - tier1_max - tier2_max
        return tier1_max, tier2_max, tier3_max


class VectorDBInterface:
    """Enhanced Vector Database Interface with better error handling"""

    def __init__(self, db_type="faiss", **kwargs):
        self.db_type = db_type
        self._vector_store = None
        self._embeddings = None

        if db_type == "faiss":
            self._setup_faiss(**kwargs)
        elif db_type == "chroma":
            self._setup_chroma(**kwargs)
        elif db_type == "pinecone":
            self._setup_pinecone(**kwargs)

    def _setup_faiss(self, embedding_model="all-MiniLM-L6-v2", index_path=None):
        """Setup FAISS with robust error handling"""
        if index_path is None:
            import sys
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(__file__)
            index_path = os.path.join(base_path, "faiss_index")

        try:
            print("🔍 Attempting to import FAISS core...")
            import faiss
            print(f"✅ FAISS core imported successfully: version {faiss.__version__}")

            print("🔍 Attempting to import LangChain FAISS wrapper...")
            from langchain_community.vectorstores import FAISS
            print("✅ LangChain FAISS wrapper imported successfully")

            print("🔍 Attempting to import HuggingFace embeddings...")
            from langchain_huggingface import HuggingFaceEmbeddings
            print("✅ HuggingFace embeddings imported successfully")

            print(f"🔍 Initializing embeddings model: {embedding_model}")
            self._embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
            print(f"✅ HuggingFace embeddings initialized: {embedding_model}")

            self.index_path = index_path
            print(f"🔍 Setting up FAISS index at: {index_path}")

            os.makedirs(os.path.dirname(index_path) if os.path.dirname(index_path) else ".", exist_ok=True)
            print(f"✅ Directory structure verified")

            try:
                print("🔍 Attempting to load existing FAISS index...")
                self._vector_store = FAISS.load_local(index_path, self._embeddings,
                                                      allow_dangerous_deserialization=True)
                print(f"✅ Loaded existing FAISS index from {index_path}")
            except Exception as e:
                print(f"⚠️ No existing index found ({str(e)[:50]}...), creating new one...")
                self._vector_store = FAISS.from_texts(["dummy_initial_text"], self._embeddings)
                self._vector_store.save_local(index_path)
                print(f"✅ Created new FAISS index at {index_path}")

            print("🎯 FAISS setup completed successfully!")

        except ImportError as e:
            print(f"❌ FAISS import failed: {str(e)}")
            print("Missing packages. Install with:")
            print("pip install faiss-cpu langchain-community")
            self._vector_store = None
        except Exception as e:
            print(f"❌ FAISS setup failed with unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            self._vector_store = None

    def _setup_chroma(self, persist_directory="./chroma_db"):
        """Setup Chroma with enhanced persistence"""
        try:
            from langchain_chroma import Chroma
            from langchain_huggingface import HuggingFaceEmbeddings

            self._embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self._vector_store = Chroma(persist_directory=persist_directory, embedding_function=self._embeddings)
            print(f"Initialized Chroma database at {persist_directory}")

        except ImportError:
            print("Chroma not available. Install with: pip install chromadb")
            self._vector_store = None

    def _setup_pinecone(self, api_key, environment, index_name):
        """Setup Pinecone with proper initialization"""
        try:
            import pinecone
            from langchain_huggingface import HuggingFaceEmbeddings

            pinecone.init(api_key=api_key, environment=environment)
            self._embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self._vector_store = pinecone.Index(index_name)
            print(f"Connected to Pinecone index: {index_name}")

        except ImportError:
            print("Pinecone not available. Install with: pip install pinecone-client")
            self._vector_store = None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Enhanced search with actual similarity scores (2026-01-23 fix)"""
        if self._vector_store is None:
            return []

        try:
            if self.db_type in ["faiss", "chroma"]:
                # Use similarity_search_with_score to get actual distances
                # Returns: List[Tuple[Document, float]] where float is L2 distance (lower = more similar)
                docs_with_scores = self._vector_store.similarity_search_with_score(query, k=top_k)
                results = []
                for i, (doc, distance) in enumerate(docs_with_scores):
                    # Convert L2 distance to similarity score (0-1 range, higher = more similar)
                    # Using: similarity = 1 / (1 + distance) which maps [0, inf) -> (0, 1]
                    similarity_score = 1.0 / (1.0 + distance)
                    # Scale to 0-10 range for consistency with existing code
                    confidence_score = similarity_score * 10.0

                    results.append({
                        "id": f"doc_{int(time.time())}_{i}",
                        "content": doc.page_content,
                        "embedding": [0.0] * 128,
                        "metadata": doc.metadata or {},
                        "timestamp": time.time(),
                        "tags": [],
                        "superseded_by": None,
                        "supersedes": None,
                        "version": 1,
                        "confidence_score": confidence_score,  # Now actual score, not hardcoded
                        "associated_missions": [],
                        "mission_relevance_scores": {}
                    })
                return results

        except Exception as e:
            print(f"Vector search error: {e}")
            return []

    def add_item(self, item: MemoryItem):
        """Enhanced item addition with mission context"""
        if self._vector_store is None:
            return

        try:
            if self.db_type in ["faiss", "chroma"]:
                from langchain_core.documents import Document

                enhanced_metadata = item.metadata.copy()
                enhanced_metadata.update({
                    "memory_id": item.id,
                    "timestamp": item.timestamp,
                    "tags": ",".join(item.tags),
                    "version": item.version,
                    "confidence_score": item.confidence_score,
                    "associated_missions": ",".join(item.associated_missions)
                })

                doc = Document(
                    page_content=item.content,
                    metadata=enhanced_metadata
                )

                if hasattr(self._vector_store, 'add_documents'):
                    self._vector_store.add_documents([doc])

                if self.db_type == "faiss" and hasattr(self, 'index_path'):
                    self._vector_store.save_local(self.index_path)

        except Exception as e:
            print(f"Vector add error: {e}")

    def embed(self, text: str) -> List[float]:
        """Generate embedding with multiple fallback strategies"""
        if self._embeddings is None:
            return self._fallback_embedding(text)

        try:
            embeddings = self._embeddings.embed_documents([text])
            return embeddings[0] if embeddings else self._fallback_embedding(text)
        except Exception:
            return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> List[float]:
        """Fallback embedding using hash-based approach"""
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        return [float(int(hash_hex[i:i + 2], 16)) / 255.0
                for i in range(0, min(len(hash_hex), 128 * 2), 2)][:128]


# ========== TEXT RAG BOOST MANAGER (2026-01-22) ========== #
# Brain-like boost mechanisms matching VISION RAG architecture
# Priority: Emotion Keywords > Timestamp (Recency) > Frequency (Access Count)

import math

class TextRAGBoostManager:
    """
    Manages brain-like boost mechanisms for TEXT RAG retrieval
    Matches VISION RAG's AsymptoticMemoryManager architecture

    Priority Order (2026-01-25 - Timestamp is DOMINANT like human brain):
    1. Timestamp (Recency) - Exponential decay with floor, optional power exponent
    2. Frequency (Access) - Logarithmic boost with cap
    3. Emotion Keywords - Multiplier for specific words (CHAT_MODE only)

    Config loaded from memory_config.json -> "text_rag_boost" section
    """

    def __init__(self):
        self.config = self._load_config_from_file()
        self._print_config()

    def _load_config_from_file(self) -> Dict:
        """Load boost parameters from memory_config.json"""
        default_config = {
            'timestamp': {
                'enabled': True,
                'decay_floor': 0.01,
                'decay_halflife_days': 30.0,
                'power': 1.0
            },
            'frequency': {
                'enabled': True,
                'boost_factor': 0.5,
                'max_boost': 3.0
            },
            'emotion': {
                'enabled': True,
                'boost_factor': 3.0,
                'enabled_modes': ['CHAT_MODE'],
                'keywords': ['love', 'hate', 'like', 'dislike', 'never', 'always', 'must', 'important', 'critical']
            }
        }

        try:
            if os.path.exists("memory_config.json"):
                with open("memory_config.json", "r") as f:
                    file_config = json.load(f)

                boost_config = file_config.get("text_rag_boost", {})

                if boost_config:
                    default_config['timestamp']['decay_halflife_days'] = boost_config.get('decay_halflife_days', 30.0)
                    default_config['timestamp']['decay_floor'] = boost_config.get('decay_floor', 0.01)
                    default_config['timestamp']['power'] = boost_config.get('timestamp_power', 1.0)
                    default_config['frequency']['boost_factor'] = boost_config.get('frequency_boost_factor', 0.5)
                    default_config['frequency']['max_boost'] = boost_config.get('max_frequency_boost', 3.0)
                    default_config['emotion']['boost_factor'] = boost_config.get('emotion_boost_factor', 3.0)
                    default_config['emotion']['keywords'] = boost_config.get('emotion_keywords',
                        ['love', 'hate', 'like', 'dislike', 'never', 'always', 'must', 'important', 'critical'])

        except Exception as e:
            print(f"⚠️ Could not load TEXT RAG boost config: {e}, using defaults")

        return default_config

    def _print_config(self):
        """Print current configuration"""
        ts = self.config['timestamp']
        fr = self.config['frequency']
        em = self.config['emotion']
        print(f"🧠 TextRAGBoostManager initialized (Asymptotic Dynamics):")
        print(f"   Decay halflife: {ts['decay_halflife_days']} days")
        print(f"   Decay floor: {ts['decay_floor']} (never reaches 0)")
        print(f"   Timestamp power: {ts['power']}")
        print(f"   Frequency boost: factor={fr['boost_factor']}, max={fr['max_boost']}")
        print(f"   Emotion boost: {em['boost_factor']}x for {len(em['keywords'])} keywords: {em['keywords']}")

    def reload_config(self):
        """Reload configuration from file (called from GUI after save)"""
        self.config = self._load_config_from_file()
        self._print_config()

    def calculate_emotion_boost(self, memory_content: str, mode: str = "CHAT_MODE") -> float:
        """
        Detect emotion keywords and return boost factor
        Only active for CHAT_MODE to prevent false positives in ACTION_MODE

        Keywords loaded from memory_config.json (customizable via GUI)
        Default: love, hate, like, dislike, never, always, must, important, critical

        Returns: boost_factor (e.g., 3.0) if keyword detected, 1.0 otherwise
        """
        if not self.config['emotion']['enabled']:
            return 1.0
        if mode not in self.config['emotion']['enabled_modes']:
            return 1.0

        content_lower = memory_content.lower()
        for keyword in self.config['emotion']['keywords']:
            if keyword.lower() in content_lower:
                return self.config['emotion']['boost_factor']

        return 1.0

    def calculate_timestamp_boost(self, memory_timestamp: float, current_time: float) -> float:
        """
        Asymptotic decay matching VISION RAG with optional power exponent
        Formula: (floor + (1 - floor) × e^(-days_old / halflife)) ^ power

        With default values (floor=0.01, halflife=30, power=1.0):
        - days=0   → 1.00 (full strength)
        - days=30  → 0.50 (half-life)
        - days=365 → 0.01 (at floor, but NEVER zero)

        With power=2.0 (optional enhancement for stronger recency):
        - days=0   → 1.00
        - days=30  → 0.25 (much weaker)
        - days=365 → 0.0001 (very weak, but still not zero)
        """
        if not self.config['timestamp']['enabled']:
            return 1.0

        days_old = (current_time - memory_timestamp) / 86400
        if days_old < 0:
            days_old = 0  # Handle future timestamps gracefully

        floor = self.config['timestamp']['decay_floor']
        halflife = self.config['timestamp']['decay_halflife_days']
        power = self.config['timestamp'].get('power', 1.0)

        # Asymptotic decay (never reaches 0)
        decay = floor + (1.0 - floor) * math.exp(-days_old / halflife)

        # Apply optional power for stronger recency bias
        if power != 1.0:
            decay = decay ** power

        return decay

    def calculate_frequency_boost(self, access_count: int) -> float:
        """
        Logarithmic frequency boost with cap
        Formula: 1.0 + min(ln(1 + count) × factor, max - 1.0)

        - count=0   → 1.0 (no boost)
        - count=10  → ~2.2
        - count=100 → 3.0 (capped)
        """
        if not self.config['frequency']['enabled']:
            return 1.0
        if access_count <= 0:
            return 1.0

        factor = self.config['frequency']['boost_factor']
        max_boost = self.config['frequency']['max_boost']

        boost = 1.0 + min(
            math.log(1 + access_count) * factor,
            max_boost - 1.0
        )
        return boost

    def calculate_final_score(self,
                              base_similarity: float,
                              memory_content: str,
                              memory_timestamp: float,
                              access_count: int,
                              current_time: float,
                              mode: str = "CHAT_MODE") -> Tuple[float, Dict[str, float]]:
        """
        Calculate final ranking score with asymptotic dynamics
        Formula: similarity × timestamp_factor × frequency_boost × emotion_boost

        Timestamp is DOMINANT because:
        1. Exponential decay rapidly reduces old memory scores
        2. Optional power exponent makes it even more dominant
        3. Floor prevents complete disappearance (like human memory)

        Returns: (final_score, boost_details_dict)
        """
        timestamp_factor = self.calculate_timestamp_boost(memory_timestamp, current_time)
        frequency_boost = self.calculate_frequency_boost(access_count)
        emotion_boost = self.calculate_emotion_boost(memory_content, mode)

        final_score = base_similarity * timestamp_factor * frequency_boost * emotion_boost

        # Calculate days_old for logging
        days_old = (current_time - memory_timestamp) / 86400

        boost_details = {
            'base_similarity': base_similarity,
            'days_old': days_old,
            'timestamp_factor': timestamp_factor,
            'timestamp_power': self.config['timestamp'].get('power', 1.0),
            'frequency_boost': frequency_boost,
            'emotion_boost': emotion_boost,
            'final_score': final_score
        }

        return final_score, boost_details

# ========== END TEXT RAG BOOST MANAGER ========== #


class AdvancedRAGCore:
    """
    Enhanced RAG system with mission-persistent context - mirrors human goal-oriented cognition
    """

    def __init__(self, vector_db=None, config_file="memory_config.json"):
        # Initialize configuration system
        self.config = MemoryConfig(config_file)

        # Initialize vector database
        self.vector_db = vector_db or VectorDBInterface("faiss")

        # Memory storage - organized by tiers like human memory
        self.memory: List[MemoryItem] = []
        self._tier1_memories: List[MemoryItem] = []
        self._tier2_memories: List[MemoryItem] = []
        self._tier3_memories: List[MemoryItem] = []

        # Mission management - like goal-oriented working memory
        self.missions: Dict[str, Mission] = {}
        self.active_mission_ids: List[str] = []  # Currently active missions, ordered by priority

        # Indexing for fast access - like neural pathways
        self._tag_index: Dict[str, List[MemoryItem]] = defaultdict(list)
        self._id_index: Dict[str, MemoryItem] = {}
        self._knowledge_lineage: Dict[str, List[str]] = defaultdict(list)
        self._mission_memory_index: Dict[str, List[str]] = defaultdict(list)  # Mission to memory IDs

        # Learning and adaptation mechanisms
        self._access_counts: Dict[str, int] = defaultdict(int)
        self._domain_patterns: Dict[str, List[str]] = defaultdict(list)
        self._mission_success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._last_id = 0
        self._save_counter = 0

        # Load existing state
        self._load_persistent_memory()
        self._load_persistent_missions()

        # Initialize brain-like boost manager for retrieval (2026-01-22)
        self.boost_manager = TextRAGBoostManager()

    def _detect_new_mission(self, user_input: str, context_history: List[str] = None) -> Optional[Dict[str, Any]]:
        """Enhanced mission detection with detailed debugging"""
        input_lower = user_input.lower()
        print(f"🔍 DEBUG: Mission detection for: '{user_input}'")

        # Skip if this is actually a completion statement
        completion_context_patterns = [
            r'\b(?:goal|mission|task|project)\s+(?:is\s+)?(?:complete|completed|finished|done)',
            r'\b(?:completed|finished|done)\s+(?:the\s+)?(?:goal|mission|task|project)',
            r'\b(?:mark\s+(?:it|this)\s+as\s+complete)',
            r'\b(?:you\s+can\s+mark)',
            r'\b(?:consider\s+(?:it|this)\s+complete)'
        ]

        for pattern in completion_context_patterns:
            if re.search(pattern, input_lower):
                print(f"❌ DEBUG: Excluded as completion context: {pattern}")
                return None

        # Skip if user is just chatting about others' work
        exclusion_patterns = [
            r'\b(?:he|she|they|someone|others?)\s+(?:need|want|plan|work)',
            r'\b(?:not|don\'t|won\'t|can\'t)\s+(?:need|want|plan)',
            r'\b(?:maybe|might|could|possibly)\s+(?:need|want)',
            r'\b(?:thinking about|considering|wondering if)'
        ]

        for pattern in exclusion_patterns:
            if re.search(pattern, input_lower):
                print(f"❌ DEBUG: Excluded by pattern: {pattern}")
                return None
        print(f"✅ DEBUG: Passed exclusion filters")

        # Enhanced mission patterns with context requirements
        '''
        mission_patterns = [
            (r'\b(?:my task is|my goal is|my project is|my target is)\s+(.{10,100})', 9, True),
            (r'\b(?:i need to complete|i have to finish|i must)\s+(.{10,100})', 8, True),
            (r'\b(?:(?:my|our|the)\s+)?(?:mission|objective|assignment|goal|target)\s+(?:is\s+)?to\s+(.{15,80})', 8,True),
            (r'\b(?:i\'m working on|i\'m building|i\'m creating)\s+(.{10,100})', 7, True),
            (r'\b(?:help me|assist me with)\s+(.{10,100})', 6, True),
            (r'\b(?:i need to|i want to|i plan to)\s+(.{15,100})', 5, False),
            (r'\b(?:let\'s work on|working on)\s+(.{15,100})', 5, False)
        ]
        '''
        # Enhanced mission patterns with context requirements
        mission_patterns = [
            # Explicit mission declarations with modifiers
            (
                r'\b(?:my|our|your|the|new)\s+(?:first|next|second|third|main|primary|current)?\s*(?:task|goal|project|target|mission|objective)\s+(?:is\s+)?(?:to\s+)?(.{10,100})', 9, True),

            # Direct mission statements
            (r'\b(?:mission|objective|assignment|goal|target)\s*(?:#?\d+|[A-Z])?\s*:\s*(.{10,100})', 9, True),

            # Completion requirements
            (r'\b(?:i need to complete|i have to finish|i must)\s+(.{10,100})', 8, True),

            # Work declarations
            (r'\b(?:i\'m working on|i\'m building|i\'m creating)\s+(.{10,100})', 7, True),

            # Standard patterns
            (r'\b(?:help me|assist me with)\s+(.{10,100})', 6, True),
            (r'\b(?:i need to|i want to|i plan to)\s+(.{15,100})', 5, False),
            (r'\b(?:let\'s work on|working on)\s+(.{15,100})', 5, False)
        ]

        for pattern, priority, is_strong in mission_patterns:
            match = re.search(pattern, input_lower)
            if match:
                title = match.group(1).strip().rstrip('.!?')
                print(f"🎯 DEBUG: Pattern matched: {pattern}")
                print(f"🎯 DEBUG: Extracted title: '{title}' (length: {len(title)})")
                print(f"🎯 DEBUG: Priority: {priority}, Strong: {is_strong}")

                # Validation checks
                if len(title) < 10:
                    print(f"❌ DEBUG: Title too short ({len(title)} < 10)")
                    continue

                if self._is_casual_statement(title):
                    print(f"❌ DEBUG: Detected as casual statement")
                    continue

                if self._is_similar_to_existing_mission(title, threshold=0.7):
                    print(f"❌ DEBUG: Similar to existing mission")
                    continue

                # For weak indicators, require additional context
                if not is_strong:
                    has_context = self._has_mission_context(user_input, context_history)
                    print(f"🔍 DEBUG: Weak indicator - has context: {has_context}")
                    if not has_context:
                        print(f"❌ DEBUG: Weak indicator without context support")
                        continue

                mission_data = {
                    "title": title.capitalize(),
                    "description": f"Detected from: {user_input[:150]}...",
                    "priority": priority,
                    "keywords": self._extract_mission_keywords(title),
                    "confidence": 0.9 if is_strong else 0.6
                }
                print(f"✅ DEBUG: Mission detected: {mission_data}")
                return mission_data

        print(f"❌ DEBUG: No mission patterns matched")
        return None

    def _is_casual_statement(self, title: str) -> bool:
        """Filter out casual daily activities with debug"""
        casual_patterns = [
            r'\b(?:eat|drink|sleep|watch|listen|buy|get)\s+(?:food|coffee|tv|music)',
            r'\b(?:go to|visit)\s+(?:store|mall|restaurant|bathroom)',
            r'\b(?:call|text|message)\s+(?:mom|dad|friend)',
            r'\b(?:take a|have a)\s+(?:break|nap|shower|walk)'
        ]

        for pattern in casual_patterns:
            if re.search(pattern, title.lower()):
                print(f"🔍 DEBUG: Casual pattern matched: {pattern}")
                return True
        return False

    def _has_mission_context(self, user_input: str, context_history: List[str]) -> bool:
        """Check if conversation has mission-oriented context with debug"""
        if not context_history:
            print(f"🔍 DEBUG: No context history available")
            return False

        recent_context = ' '.join(context_history[-3:]).lower()
        mission_context_indicators = [
            'project', 'task', 'work', 'build', 'develop', 'research',
            'complete', 'finish', 'goal', 'objective', 'deadline'
        ]

        matches = sum(1 for word in mission_context_indicators if word in recent_context)
        print(f"🔍 DEBUG: Mission context indicators found: {matches}/2 required")
        print(f"🔍 DEBUG: Recent context: '{recent_context[:100]}...'")

        return matches >= 2

    def _is_similar_to_existing_mission(self, title: str, threshold: float = 0.7) -> bool:
        """Check similarity with debug - MODIFIED to add logging"""
        title_words = set(title.lower().split())

        for mission in self.missions.values():
            if mission.status == "active":
                existing_words = set(mission.title.lower().split())
                overlap = len(title_words.intersection(existing_words)) / len(title_words.union(existing_words))
                print(f"🔍 DEBUG: Similarity to '{mission.title}': {overlap:.2f}")
                if overlap > threshold:
                    return True
        return False

    def _extract_mission_keywords(self, title: str) -> List[str]:
        """Extract relevant keywords from mission title"""
        words = title.lower().split()
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'a', 'an'}
        return [w for w in words if w not in stop_words and len(w) > 2][:5]

    def _check_mission_completion(self, user_input: str, ai_response: str) -> None:
        """Enhanced completion detection with detailed debugging"""
        content_to_check = user_input.lower()  # Only check user input
        print(f"🔍 DEBUG: Checking completion for: '{user_input[:50]}...'")

        # Exclude false signals
        negative_patterns = [
            r'\b(?:not|never|hardly|barely)\s+(?:completed|finished|done)',
            r'\b(?:still|yet to be|remains to be)\s+(?:completed|finished|done)',
            r'\b(?:he|she|they|someone else)\s+(?:completed|finished)',
            r'\b(?:almost|nearly|partially)\s+(?:completed|finished|done)'
        ]

        for pattern in negative_patterns:
            if re.search(pattern, content_to_check):
                print(f"❌ DEBUG: Excluded by negative pattern: {pattern}")
                return
        print(f"✅ DEBUG: Passed negative pattern filters")

        # Enhanced completion indicators
        completion_indicators = {
            'explicit_completion': [
                r'\b(?:i have|i\'ve)\s+(?:completed|finished|done)',
                r'\b(?:task|project|mission|goal|target)\s+(?:is\s+)?(?:completed|finished|done)',
                r'\b(?:successfully|finally)\s+(?:completed|finished|accomplished)',
                # Fixed patterns to allow text between:
                r'\b(?:goal|mission|target|task|project)\s+.*?\s+(?:is\s+)?complete',
                r'\b(?:goal|mission|target|task|project)\s+.*?\s+(?:is\s+)?(?:completed|finished|done)',
                r'\bmark\s+(?:it|this)\s+(?:as\s+)?complete',
                r'\byou\s+can\s+mark\s+(?:it|this)\s+(?:as\s+)?complete'
            ],
            'outcome_statements': [
                r'\b(?:achieved|accomplished|succeeded|solved)',
                r'\b(?:working perfectly|problem solved|all set)',
                r'\b(?:mission accomplished|task complete)'
            ],
            'closure_language': [
                r'\b(?:wrap(?:ped)? up|concluded|finalized)',
                r'\b(?:ready to move on|moving to next)',
                r'\b(?:that\'s it|we\'re done|all finished)'
            ]
        }

        # Count different types of completion signals
        signal_count = 0
        signal_types = []

        for signal_type, patterns in completion_indicators.items():
            for pattern in patterns:
                if re.search(pattern, content_to_check):
                    print(f"🎯 DEBUG: Found {signal_type} signal: {pattern}")
                    signal_count += 1
                    signal_types.append(signal_type)
                    break

        print(f"🔍 DEBUG: Total completion signals: {signal_count}, Types: {signal_types}")

        # Require multiple signals or strong explicit completion
        if signal_count < 2 and 'explicit_completion' not in signal_types:
            print(f"❌ DEBUG: Insufficient completion signals ({signal_count} < 2 and no explicit)")
            return

        print(f"✅ DEBUG: Sufficient completion signals detected")

        # STEP 1: Try to EXTRACT mission title from completion statement
        # Patterns like "mission [TITLE] is complete" or "our mission about [TITLE] is complete"
        title_patterns = [
            r'(?:mission|goal|task|target|project)\s+(?:about\s+)?(.+?)\s+(?:is\s+)?(?:complete|finished|done)',
            r'(?:mission|goal|task|target|project)\s+(.+?)\s+(?:complete|finished|done)',
        ]

        extracted_title = None
        for pattern in title_patterns:
            match = re.search(pattern, content_to_check, re.IGNORECASE)
            if match:
                extracted_title = match.group(1).strip()
                print(f"🎯 DEBUG: Extracted mission title from input: '{extracted_title}'")
                break

        # STEP 2: Find missions - prioritize EXACT title match first
        candidate_missions = []
        for mission in list(self.missions.values()):
            if mission.status != "active":
                continue

            # Check 1: EXACT title substring match (highest priority)
            exact_match = False
            if extracted_title:
                # Check if extracted title is in mission title or vice versa
                if extracted_title.lower() in mission.title.lower() or mission.title.lower() in extracted_title.lower():
                    exact_match = True
                    print(f"✅ DEBUG: EXACT TITLE MATCH: '{mission.title[:50]}...' matches '{extracted_title}'")

            # Check 2: Relevance and keyword match (lower priority)
            relevance = mission.is_relevant_to_query(content_to_check)
            keyword_match = any(kw.lower() in content_to_check for kw in mission.context_keywords)

            print(f"🔍 DEBUG: Mission '{mission.title[:30]}...'")
            print(f"🔍 DEBUG: Mission keywords: {mission.context_keywords}")
            print(f"🔍 DEBUG: Exact title match: {exact_match}, Relevance: {relevance:.2f}, Keyword match: {keyword_match}")

            # Prioritize missions: exact match first, then relevance/keywords
            if exact_match:
                candidate_missions.insert(0, mission)  # Add to front (highest priority)
            elif relevance > 0.4 or keyword_match:
                candidate_missions.append(mission)  # Add to end (lower priority)

        # STEP 3: Try to complete the first matching mission
        for mission in candidate_missions:
            print(f"🎯 DEBUG: Trying to complete mission: '{mission.title}'")
            if self._validate_mission_completion(mission, user_input, ai_response):
                print(f"🎉 DEBUG: Mission completed with {signal_count} signals: {mission.title}")
                self.complete_mission(mission.id)
                return
            else:
                print(f"❌ DEBUG: Mission completion validation failed for '{mission.title[:30]}...'")

        print(f"❌ DEBUG: No mission matched completion criteria")

    def _validate_mission_completion(self, mission: Mission, user_input: str, ai_response: str) -> bool:
        """Additional validation with debug"""
        print(f"🔍 DEBUG: Validating completion for mission: {mission.title}")

        # Check for completion criteria if defined
        if mission.completion_criteria:
            criteria_met = sum(1 for criteria in mission.completion_criteria
                               if criteria.lower() in f"{user_input} {ai_response}".lower())
            print(f"🔍 DEBUG: Completion criteria: {criteria_met}/{len(mission.completion_criteria)} met")
            if criteria_met < len(mission.completion_criteria) * 0.6:
                print(f"❌ DEBUG: Insufficient criteria met ({criteria_met} < {len(mission.completion_criteria) * 0.6})")
                return False

        # Check mission progress indicators
        completion_signals = mission.progress_indicators.get('completion_signals', 0)
        print(f"🔍 DEBUG: Previous completion signals: {completion_signals}")

        # INCREMENT FIRST, THEN CHECK
        mission.progress_indicators['completion_signals'] = completion_signals + 1
        new_count = mission.progress_indicators['completion_signals']
        print(f"📈 DEBUG: Incremented completion signals to {new_count}")

        if new_count < 2:  # Require at least 2 signals
            print(f"❌ DEBUG: Need more signals ({new_count} < 2)")
            return False

        print(f"✅ DEBUG: Mission validation passed with {new_count} signals")
        return True

    def _auto_pause_inactive_missions(self):
        """Enhanced auto-pause with user abandonment detection"""
        pause_threshold_days = self.config.config.get("mission_auto_pause_days", 7)
        pause_threshold_seconds = pause_threshold_days * 24 * 3600
        current_time = time.time()

        paused_count = 0
        for mission_id in self.active_mission_ids[:]:
            mission = self.missions.get(mission_id)
            if mission and (current_time - mission.last_activity_time) > pause_threshold_seconds:
                print(f"🎯 Auto-pausing inactive mission: {mission.title}")
                mission.status = "paused"
                self.active_mission_ids.remove(mission_id)
                paused_count += 1

        if paused_count > 0:
            print(f"Auto-paused {paused_count} inactive missions")

    def _generate_id(self, prefix: str = "mem") -> str:
        """Generate unique ID for memory items or missions"""
        self._last_id += 1
        return f"{prefix}_{int(time.time() * 1000)}_{self._last_id}"

    def _create_embedding(self, text: str) -> List[float]:
        """Generate embedding using vector DB or fallback"""
        return self.vector_db.embed(text)

    def _extract_tags(self, text: str) -> List[str]:
        """Extract meaningful keywords as tags for memory organization"""
        words = text.lower().split()
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'is', 'are',
            'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'must', 'ought'
        }
        tags = [w.strip('.,!?";()[]{}') for w in words
                if w not in stop_words and len(w) > 2 and w.isalpha()]
        return list(set(tags[:15]))

    def _advanced_importance_analysis(self, content: str, context: str = "", active_missions: List[Mission] = None) -> \
    Tuple[int, List[str], int, float]:
        """
        Enhanced importance analysis with mission-aware scoring
        Returns: (priority_score, special_tags, tier, confidence_score)
        """
        content_lower = content.lower()
        context_lower = context.lower()
        active_missions = active_missions or []

        # Tier 1: Core biographical facts and critical safety information
        tier1_patterns = [
            # Core identity facts
            r'\b(my name is|i am called|call me)\s+([A-Z][a-z]+)',
            r'\b(i was born|my birthday is|my birthdate is)\s+(.{5,})',
            r'\b(i live in|i am from|my address is)\s+(.{5,})',

            # Critical safety/medical facts with explicit permanence
            r'\b(never forget|always remember).*(allergic to|medical condition|emergency|critical)',
            r'\b(my social security|my passport number|my ID number)\s+',

            # Absolute factual corrections
            r'\b(never forget|always remember)\s+(?:that\s+)?(.{20,})\s+(fact|truth|reality)'
        ]

        # Tier 2: Strong behavioral knowledge and preferences
        tier2_patterns = [
            # Behavioral instructions and preferences
            r'\b(never|always|remember|don\'t ever)\s+(reply|respond|do|use|store|be|say|tell)',
            r'\b(i|my|you|your|our)\s+(prefer|like|hate|usually|typically|generally|always)',

            # Strong assertions and proven knowledge
            r'\b(definitely|obviously|clearly|certainly|actually)\s+(.{10,})',
            r'\b(this (works|worked|helps|is effective|is successful))\s+(.{10,})',
            r'\b(the (best|better|optimal|correct) way)\s+(.{10,})',
            r'\b(avoid|don\'t use|never use|not recommended)\s+(.{10,})',

            # Knowledge corrections and updates
            r'\b(actually|correction|wrong|mistake)\s+(.{10,})',
            r'\b(let me (correct|fix|update))\s+(.{10,})',

            # Professional and procedural knowledge
            r'\b(essential|crucial|important|vital)\s+(.{10,})',
            r'\b(solved|fixed|working solution)\s+(.{10,})'
        ]

        # Tier 3: Contextual and temporal knowledge
        tier3_patterns = [
            # Temporal and contextual information
            r'\b(today|tomorrow|this week|this month|currently|right now|at the moment)\s+(.{5,})',
            r'\b(planning to|thinking about|considering|might|could|perhaps|maybe)\s+(.{10,})',

            # Active mission context
            r'\b(working on|building|creating|developing|researching)\s+(.{10,})',
            r'\b(project|task|assignment|goal|objective)\s+(.{10,})',

            # Suggestions and experimental ideas
            r'\b(suggestion|recommendation|idea|thought|could try)\s+(.{5,})',
            r'\b(example|instance|case|scenario)\s+(.{5,})',

            # Daily activities and temporary states
            r'\b(meeting|appointment|visit|call|trip)\s+(.{10,})',
            r'\b(feeling|mood|energy|focus)\s+(.{5,})'
        ]

        # Analyze base patterns
        tier = 3
        priority_score = 5
        confidence_score = 5.0
        special_tags = []

        for pattern in tier1_patterns:
            if re.search(pattern, content_lower):
                tier = 1
                priority_score = 10
                confidence_score = 9.0
                special_tags.extend(["permanent_memory", "tier1_knowledge"])
                break

        if tier != 1:
            for pattern in tier2_patterns:
                if re.search(pattern, content_lower):
                    tier = 2
                    priority_score = 8
                    confidence_score = 7.0
                    special_tags.extend(["high_persistence", "tier2_knowledge"])
                    break

        if tier == 3:
            for pattern in tier3_patterns:
                if re.search(pattern, content_lower):
                    priority_score = 6
                    confidence_score = 6.0
                    special_tags.extend(["standard_memory", "tier3_knowledge"])
                    break

        # Mission-aware importance boost - this is the key enhancement
        mission_boost = 0
        mission_tags = []

        for mission in active_missions:
            relevance = mission.is_relevant_to_query(content)
            if relevance > 0.3:  # Significant relevance to active mission
                mission_boost += relevance * mission.priority * 0.5  # Scale by mission priority
                mission_tags.append(f"mission_{mission.id}")
                special_tags.append(f"relevant_to_{mission.title[:20]}")

                # Mission progress and completion patterns get extra importance
                progress_patterns = [
                    r'\b(completed|finished|done|accomplished|achieved)\b',
                    r'\b(progress|advancement|breakthrough|discovery)\b',
                    r'\b(obstacle|problem|challenge|difficulty) (overcome|solved|resolved)\b',
                    r'\b(learned|discovered|found out|realized)\b'
                ]

                if any(re.search(pattern, content_lower) for pattern in progress_patterns):
                    mission_boost += 1.0
                    special_tags.append("mission_progress")

        # Apply mission boost
        priority_score = min(10, priority_score + mission_boost)
        confidence_score = min(10.0, confidence_score + (mission_boost * 0.5))

        # Domain-specific learning enhancement
        domain_boost = self._analyze_domain_importance(content_lower)
        priority_score = min(10, priority_score + domain_boost)

        # Identity and personal information detection
        identity_patterns = [
            r'\b(my name|my age|my gender|my country|my birthday)\b',
            r'\b(i am|i live in|i work as|i study)\b'
        ]

        identity_detected = any(re.search(pattern, content_lower) for pattern in identity_patterns)
        if identity_detected and tier > 1:
            tier = 1
            priority_score = 10
            confidence_score = 9.0
            special_tags.extend(["user_identity", "permanent_memory"])

        # Correction and override detection
        correction_patterns = [
            r'\b(actually|correction|wrong|mistake|error in previous)\b',
            r'\b(not (correct|right|true)|that\'s (wrong|incorrect))\b',
            r'\b(let me (correct|fix) that)\b'
        ]

        if any(re.search(pattern, content_lower) for pattern in correction_patterns):
            special_tags.append("correction_detected")
            confidence_score += 1.0

        special_tags.extend(mission_tags)
        return priority_score, special_tags, tier, confidence_score

    def _analyze_domain_importance(self, content: str) -> int:
        """Learn domain-specific importance patterns over time"""
        domain_indicators = {
            'coding': ['code', 'function', 'variable', 'syntax', 'compile', 'debug', 'programming'],
            'medical': ['patient', 'diagnosis', 'treatment', 'medicine', 'symptoms', 'doctor'],
            'business': ['strategy', 'market', 'revenue', 'profit', 'customer', 'sales'],
            'education': ['learn', 'study', 'knowledge', 'teach', 'understanding', 'concept'],
            'science': ['research', 'experiment', 'hypothesis', 'data', 'analysis', 'theory'],
            'daily_life': ['shopping', 'family', 'friends', 'home', 'personal', 'routine'],
            'travel': ['trip', 'travel', 'visit', 'location', 'journey', 'destination']
        }

        detected_domain = None
        max_matches = 0

        for domain, keywords in domain_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in content)
            if matches > max_matches:
                max_matches = matches
                detected_domain = domain

        if detected_domain and max_matches >= 2:
            if self.config.config.get("domain_adaptation", True):
                self._domain_patterns[detected_domain].extend(content.split()[:5])
            return min(2, max_matches)

        return 0

    def _handle_knowledge_evolution(self, new_item: MemoryItem) -> Optional[MemoryItem]:
        """Handle knowledge evolution and corrections with mission context"""
        if "correction_detected" not in new_item.tags:
            return new_item

        similar_memories = self._semantic_search(new_item.content, top_k=10)

        for existing_memory in similar_memories:
            if existing_memory.superseded_by is not None:
                continue

            content_similarity = self._calculate_content_similarity(new_item.content, existing_memory.content)

            if content_similarity > 0.7:
                new_confidence = new_item.confidence_score
                old_confidence = existing_memory.confidence_score
                #threshold = self.config.config.get("confidence_threshold_override", 8.0)

                # Get tier-specific evolution thresholds
                existing_tier = existing_memory.metadata.get("tier", 3)
                print(f"🔄 EVOLUTION CHECK: Existing memory '{existing_memory.id}' is Tier {existing_tier}")
                print(f"🔄 EVOLUTION CHECK: Existing confidence: {existing_memory.confidence_score}")
                print(f"🔄 EVOLUTION CHECK: New confidence: {new_confidence}")

                if existing_tier == 1:
                    threshold = self.config.config.get("tier1_evolution_threshold", 9.0)
                    print(f"🔒 TIER 1 EVOLUTION: Threshold = {threshold}, requires explicit correction language")

                    # Require explicit correction language for Tier 1
                    correction_language = [
                        r'\b(actually|correction|i was wrong|let me correct)\s+',
                        r'\b(i need to (correct|fix|update))\s+',
                        r'\b(that\'s (wrong|incorrect|not right))\s+'
                    ]
                    has_correction_language = any(re.search(pattern, new_item.content.lower())
                                                  for pattern in correction_language)

                    print(f"🔒 TIER 1 CHECK: Has correction language = {has_correction_language}")
                    if not has_correction_language:
                        print(f"❌ TIER 1 EVOLUTION BLOCKED: No explicit correction language found")
                        continue

                    if new_confidence < threshold:
                        print(f"❌ TIER 1 EVOLUTION BLOCKED: Confidence {new_confidence} < {threshold}")
                        continue

                    print(f"✅ TIER 1 EVOLUTION APPROVED: High confidence + explicit correction")

                elif existing_tier == 2:
                    threshold = self.config.config.get("tier2_evolution_threshold", 7.0)
                    print(f"🔓 TIER 2 EVOLUTION: Threshold = {threshold}")

                    if new_confidence < threshold:
                        print(f"❌ TIER 2 EVOLUTION BLOCKED: Confidence {new_confidence} < {threshold}")
                        continue

                    print(f"✅ TIER 2 EVOLUTION APPROVED: Confidence meets threshold")

                else:  # Tier 3
                    threshold = self.config.config.get("tier3_evolution_threshold", 5.0)
                    print(f"🔀 TIER 3 EVOLUTION: Threshold = {threshold}")

                    if new_confidence < threshold:
                        print(f"❌ TIER 3 EVOLUTION BLOCKED: Confidence {new_confidence} < {threshold}")
                        continue

                    print(f"✅ TIER 3 EVOLUTION APPROVED: Easy update threshold met")

                # Final confidence comparison check
                if new_confidence <= old_confidence:
                    print(
                        f"❌ EVOLUTION BLOCKED: New confidence {new_confidence} not higher than existing {old_confidence}")
                    continue

                print(f"🎉 KNOWLEDGE EVOLUTION EXECUTING:")
                print(f"  📝 Old memory: '{existing_memory.content[:50]}...'")
                print(f"  📝 New memory: '{new_item.content[:50]}...'")
                print(f"  🔢 Confidence: {old_confidence} → {new_confidence}")
                print(f"  📊 Tier: {existing_tier}")

                if new_confidence >= threshold and new_confidence > old_confidence:
                    new_item.supersedes = existing_memory.id
                    new_item.version = existing_memory.version + 1
                    existing_memory.superseded_by = new_item.id

                    self._knowledge_lineage[new_item.id].append(existing_memory.id)

                    new_item.tags.append("knowledge_evolution")
                    new_item.tags.append(f"supersedes_{existing_memory.id}")

                    # Update mission associations if applicable
                    new_item.associated_missions.extend(existing_memory.associated_missions)

                    print(f"Knowledge evolution: Memory {new_item.id} supersedes {existing_memory.id}")
                    break

        return new_item

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate semantic similarity between two pieces of content"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _semantic_search(self, query: str, top_k: int = 5, include_superseded: bool = False,
                         mission_filter: str = None, mode: str = "CHAT_MODE") -> List[MemoryItem]:
        """
        Enhanced semantic search with brain-like boost mechanisms (2026-01-22)
        Now includes: Memory Split between CHAT [USER] and ACTION [ACTION] (2026-01-31)

        Split retrieval ensures balanced view of:
        - [USER] memories: Conversations with user (left hemisphere)
        - [ACTION] memories: Facts discovered through agents (right hemisphere)
        """
        current_time = time.time()

        # Load memory split configuration
        split_config = self.config.config.get("memory_split", {})
        split_enabled = split_config.get("enabled", True)
        chat_percent = split_config.get("chat_percent", 50)
        action_percent = split_config.get("action_percent", 50)
        min_per_category = split_config.get("min_per_category", 1)
        chat_fills_if_empty = split_config.get("chat_fills_if_action_empty", True)

        # Normalize percentages
        total_percent = chat_percent + action_percent
        if total_percent > 0:
            chat_ratio = chat_percent / total_percent
            action_ratio = action_percent / total_percent
        else:
            chat_ratio = 0.5
            action_ratio = 0.5

        # Calculate targets
        chat_target = max(min_per_category, int(top_k * chat_ratio))
        action_target = max(min_per_category, int(top_k * action_ratio))

        # Adjust for rounding (ensure total = top_k)
        if chat_target + action_target > top_k:
            if chat_target > action_target:
                chat_target = top_k - action_target
            else:
                action_target = top_k - chat_target
        elif chat_target + action_target < top_k:
            chat_target = top_k - action_target

        print(f"🧠 MEMORY SPLIT: Target {chat_target} [USER] + {action_target} [ACTION] (split_enabled={split_enabled})")

        # ========== STEP 1: Get all candidates from FAISS ==========
        if self.vector_db:
            try:
                print(f"🔍 Using FAISS vector search for: '{query[:30]}...' (mode: {mode})")
                # Get MANY more candidates for split filtering (2026-01-31)
                # Need large pool because [ACTION] memories (60) are rare vs [USER]+untagged (4156)
                # Fetching 50x ensures we get enough variety to find [ACTION] memories
                vector_results = self.vector_db.search(query, min(top_k * 50, 500))

                chat_candidates = []  # [USER] memories
                action_candidates = []  # [ACTION] memories
                seen_memory_ids = set()

                # DEBUG: Track matching statistics (2026-01-31)
                debug_no_id = 0
                debug_not_in_index = 0

                for result in vector_results:
                    memory_id = result.get("metadata", {}).get("memory_id")
                    if not memory_id:
                        debug_no_id += 1
                        continue
                    if memory_id not in self._id_index:
                        debug_not_in_index += 1
                        continue
                    if memory_id and memory_id in self._id_index:
                        if memory_id in seen_memory_ids:
                            continue
                        seen_memory_ids.add(memory_id)

                        memory_item = self._id_index[memory_id]

                        if not include_superseded and memory_item.superseded_by is not None:
                            continue

                        if mission_filter and mission_filter not in memory_item.associated_missions:
                            continue

                        # Get base similarity from FAISS result
                        base_similarity = result.get("confidence_score", 5.0) / 10.0

                        # ========== SPLIT BY MODE TAG ==========
                        if split_enabled:
                            content = memory_item.content
                            if "[ACTION]" in content:
                                action_candidates.append((memory_item, base_similarity))
                            else:
                                chat_candidates.append((memory_item, base_similarity))
                        else:
                            chat_candidates.append((memory_item, base_similarity))

                # DEBUG: Print matching statistics
                if debug_no_id > 0 or debug_not_in_index > 0:
                    print(f"🔍 DEBUG: FAISS returned {len(vector_results)} results. Skipped: {debug_no_id} no_id, {debug_not_in_index} not_in_index")

                # ========== STEP 2: Apply boosts within each category ==========
                def apply_boosts(candidates):
                    boosted = []
                    for memory_item, base_sim in candidates:
                        access_count = self._access_counts.get(memory_item.id, 0)
                        final_score, boost_details = self.boost_manager.calculate_final_score(
                            base_similarity=base_sim,
                            memory_content=memory_item.content,
                            memory_timestamp=memory_item.timestamp,
                            access_count=access_count,
                            current_time=current_time,
                            mode=mode
                        )
                        boosted.append((memory_item, final_score, boost_details))
                    boosted.sort(key=lambda x: x[1], reverse=True)
                    return boosted

                chat_boosted = apply_boosts(chat_candidates)
                action_boosted = apply_boosts(action_candidates)

                print(f"📊 CANDIDATES: {len(chat_boosted)} [USER] | {len(action_boosted)} [ACTION]")

                # ========== FALLBACK: Fetch recent [ACTION] memories if none found ==========
                # This ensures ACTION memories are retrieved even when query is unrelated to them
                if len(action_boosted) == 0 and split_enabled:
                    print(f"🔄 FALLBACK: Fetching recent [ACTION] memories directly from memory...")
                    action_memories_direct = []
                    for item in sorted(self.memory, key=lambda x: x.timestamp, reverse=True):
                        if "[ACTION]" in item.content:
                            # Calculate boost for this memory
                            access_count = self._access_counts.get(item.id, 0)
                            # Use a base similarity of 0.3 (lower than FAISS but not zero)
                            final_score, boost_details = self.boost_manager.calculate_final_score(
                                base_similarity=0.3,
                                memory_content=item.content,
                                memory_timestamp=item.timestamp,
                                access_count=access_count,
                                current_time=current_time,
                                mode=mode
                            )
                            action_memories_direct.append((item, final_score, boost_details))
                            if len(action_memories_direct) >= action_target * 2:  # Get 2x for buffer
                                break
                    if action_memories_direct:
                        action_boosted = sorted(action_memories_direct, key=lambda x: x[1], reverse=True)
                        print(f"✅ FALLBACK: Found {len(action_boosted)} [ACTION] memories from direct search")

                # ========== STEP 3: Handle edge cases ==========
                final_results = []

                actual_chat_count = min(chat_target, len(chat_boosted))
                actual_action_count = min(action_target, len(action_boosted))

                # Handle ACTION shortage
                if actual_action_count < action_target:
                    shortage = action_target - actual_action_count
                    if chat_fills_if_empty and len(chat_boosted) > actual_chat_count:
                        extra_chat = min(shortage, len(chat_boosted) - actual_chat_count)
                        actual_chat_count += extra_chat
                        if actual_action_count == 0:
                            print(f"⚠️ WARNING: No [ACTION] memories found. Using {actual_chat_count} [USER] memories only.")
                        else:
                            print(f"⚠️ WARNING: Only {actual_action_count} [ACTION] memories (wanted {action_target}). Filled with {extra_chat} extra [USER].")

                # Handle CHAT shortage
                if actual_chat_count < chat_target:
                    shortage = chat_target - actual_chat_count
                    if len(action_boosted) > actual_action_count:
                        extra_action = min(shortage, len(action_boosted) - actual_action_count)
                        actual_action_count += extra_action
                        if actual_chat_count == 0:
                            print(f"⚠️ WARNING: No [USER] memories found. Using {actual_action_count} [ACTION] memories only.")
                        else:
                            print(f"⚠️ WARNING: Only {actual_chat_count} [USER] memories (wanted {chat_target}). Filled with {extra_action} extra [ACTION].")

                # ========== STEP 4: Collect final results ==========
                for i, (mem, score, details) in enumerate(chat_boosted[:actual_chat_count]):
                    final_results.append((mem, score, details, "USER"))

                for i, (mem, score, details) in enumerate(action_boosted[:actual_action_count]):
                    final_results.append((mem, score, details, "ACTION"))

                # Sort final results by score
                final_results.sort(key=lambda x: x[1], reverse=True)

                # ========== STEP 5: Log results ==========
                if final_results:
                    print(f"✅ FINAL SPLIT: {actual_chat_count} [USER] + {actual_action_count} [ACTION] = {len(final_results)} total")
                    print(f"="*80)
                    for i, (mem, score, details, mem_type) in enumerate(final_results[:10]):
                        days_old = (current_time - mem.timestamp) / 86400
                        from datetime import datetime
                        mem_datetime = datetime.fromtimestamp(mem.timestamp).strftime('%Y-%m-%d %H:%M')
                        print(f"   {i+1}. [{mem_type}] Score={score:.4f} | days_old={days_old:.1f}d | date={mem_datetime}")
                        print(f"      sim={details['base_similarity']:.3f} × time={details['timestamp_factor']:.3f} × "
                              f"freq={details['frequency_boost']:.2f} × emo={details['emotion_boost']:.1f}")
                        print(f"      Content: '{mem.content[:150]}...'")
                        print(f"      ---")
                    print(f"="*80)

                    return [item for item, score, details, mem_type in final_results[:top_k]]

            except Exception as e:
                print(f"Vector search failed, falling back to local search: {e}")

        # ========== FALLBACK: Local semantic search with split ==========
        query_vec = self._create_embedding(query)

        active_memories = [m for m in self.memory
                           if include_superseded or m.superseded_by is None]

        if mission_filter:
            active_memories = [m for m in active_memories
                               if mission_filter in m.associated_missions]

        # Remove duplicates by ID
        seen_ids = set()
        deduplicated_memories = []
        for m in active_memories:
            if m.id not in seen_ids:
                seen_ids.add(m.id)
                deduplicated_memories.append(m)
        active_memories = deduplicated_memories

        # Split into categories
        chat_memories = []
        action_memories = []

        for item in active_memories:
            dot = sum(a * b for a, b in zip(query_vec, item.embedding))
            norm_a = sum(a * a for a in query_vec) ** 0.5
            norm_b = sum(b * b for b in item.embedding) ** 0.5

            if norm_a == 0 or norm_b == 0:
                base_sim = 0.0
            else:
                base_sim = dot / (norm_a * norm_b)

            access_count = self._access_counts.get(item.id, 0)
            final_score, boost_details = self.boost_manager.calculate_final_score(
                base_similarity=base_sim,
                memory_content=item.content,
                memory_timestamp=item.timestamp,
                access_count=access_count,
                current_time=current_time,
                mode=mode
            )

            if split_enabled and "[ACTION]" in item.content:
                action_memories.append((item, final_score))
            else:
                chat_memories.append((item, final_score))

        # Sort each category
        chat_memories.sort(key=lambda x: x[1], reverse=True)
        action_memories.sort(key=lambda x: x[1], reverse=True)

        # Combine with split ratios and handle shortages
        results = []
        results.extend(chat_memories[:chat_target])
        results.extend(action_memories[:action_target])

        if len(action_memories) < action_target and chat_fills_if_empty:
            extra_needed = action_target - len(action_memories)
            extra_chat = chat_memories[chat_target:chat_target + extra_needed]
            results.extend(extra_chat)
            if len(action_memories) == 0:
                print(f"⚠️ WARNING: No [ACTION] memories found in local search.")

        results.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in results[:top_k]]

    def _organize_by_tiers(self):
        """Organize memories into tiers for intelligent memory management"""
        self._tier1_memories.clear()
        self._tier2_memories.clear()
        self._tier3_memories.clear()

        for memory in self.memory:
            tier = memory.metadata.get("tier", 3)
            if tier == 1 or "permanent_memory" in memory.tags:
                self._tier1_memories.append(memory)
            elif tier == 2:
                self._tier2_memories.append(memory)
            else:
                self._tier3_memories.append(memory)

    def _intelligent_pruning(self):
        """Intelligent memory pruning that respects tiers and mission associations"""
        total_memories = len(self.memory)
        max_memories = self.config.config["max_total_memories"]

        if total_memories <= max_memories:
            return

        self._organize_by_tiers()

        tier1_max, tier2_max, tier3_max = self.config.get_tier_limits()

        if len(self._tier1_memories) > tier1_max:
            print(f"Warning: {len(self._tier1_memories)} permanent memories exceed recommended limit of {tier1_max}")

        if len(self._tier2_memories) > tier2_max:
            tier2_to_remove = len(self._tier2_memories) - tier2_max
            self._prune_tier2_memories(tier2_to_remove)

        current_tier3_limit = max_memories - len(self._tier1_memories) - len(self._tier2_memories)
        if len(self._tier3_memories) > current_tier3_limit:
            tier3_to_remove = len(self._tier3_memories) - current_tier3_limit
            self._prune_tier3_memories(tier3_to_remove)

    def _prune_tier2_memories(self, count_to_remove: int):
        """Prune Tier 2 memories with mission awareness"""

        def tier2_priority(memory):
            base_priority = memory.metadata.get("priority", 5)
            access_boost = self._access_counts.get(memory.id, 0) * 0.3
            age_days = (time.time() - memory.timestamp) / (24 * 3600)
            time_penalty = age_days * 0.1

            # Mission association boost
            mission_boost = 0
            for mission_id in memory.associated_missions:
                if mission_id in self.active_mission_ids:
                    mission_boost += 2.0  # Strong boost for active mission memories
                elif mission_id in self.missions:
                    mission_boost += 0.5  # Smaller boost for inactive missions

            return base_priority + access_boost + mission_boost - time_penalty

        sorted_tier2 = sorted(self._tier2_memories, key=tier2_priority, reverse=True)
        memories_to_remove = sorted_tier2[-count_to_remove:]

        for memory in memories_to_remove:
            self._remove_memory(memory)

    def _prune_tier3_memories(self, count_to_remove: int):
        """Prune Tier 3 memories with mission awareness"""

        def tier3_priority(memory):
            base_priority = memory.metadata.get("priority", 5)
            access_boost = self._access_counts.get(memory.id, 0) * 0.5
            age_days = (time.time() - memory.timestamp) / (24 * 3600)
            time_penalty = age_days * 0.15

            evolution_boost = 1.0 if memory.supersedes or memory.superseded_by else 0.0

            # Mission association boost
            mission_boost = 0
            for mission_id in memory.associated_missions:
                if mission_id in self.active_mission_ids:
                    mission_boost += 1.5
                elif mission_id in self.missions:
                    mission_boost += 0.3

            return base_priority + access_boost + evolution_boost + mission_boost - time_penalty

        sorted_tier3 = sorted(self._tier3_memories, key=tier3_priority, reverse=True)
        memories_to_remove = sorted_tier3[-count_to_remove:]

        for memory in memories_to_remove:
            self._remove_memory(memory)

    def _remove_memory(self, memory: MemoryItem):
        """Safely remove a memory from all data structures"""
        if memory in self.memory:
            self.memory.remove(memory)

        for tier_list in [self._tier1_memories, self._tier2_memories, self._tier3_memories]:
            if memory in tier_list:
                tier_list.remove(memory)

        if memory.id in self._id_index:
            del self._id_index[memory.id]

        for tag in memory.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [m for m in self._tag_index[tag] if m.id != memory.id]

        if memory.id in self._knowledge_lineage:
            del self._knowledge_lineage[memory.id]

        # Clean up mission associations
        for mission_id in memory.associated_missions:
            if mission_id in self._mission_memory_index:
                self._mission_memory_index[mission_id] = [
                    mid for mid in self._mission_memory_index[mission_id] if mid != memory.id
                ]

    def _update_indices(self, item: MemoryItem):
        """Update all indexing structures for fast access"""
        self._id_index[item.id] = item
        for tag in item.tags:
            self._tag_index[tag].append(item)

        # Update mission memory index
        for mission_id in item.associated_missions:
            self._mission_memory_index[mission_id].append(item.id)

    def _save_persistent_memory(self):
        """Save memory state to disk for persistence across sessions"""
        try:
            memory_data = {
                "memories": [item.to_dict() for item in self.memory],
                "access_counts": dict(self._access_counts),
                "domain_patterns": dict(self._domain_patterns),
                "knowledge_lineage": dict(self._knowledge_lineage),
                "mission_memory_index": dict(self._mission_memory_index),
                "mission_success_patterns": dict(self._mission_success_patterns),
                "last_id": self._last_id
            }

            os.makedirs("ChatHistory", exist_ok=True)
            with open("ChatHistory/persistent_memory.json", "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=2)

        except Exception as e:
            print(f"Failed to save persistent memory: {e}")

    def _load_persistent_memory(self):
        """Load memory state from disk"""
        try:
            if os.path.exists("ChatHistory/persistent_memory.json"):
                with open("ChatHistory/persistent_memory.json", "r", encoding="utf-8") as f:
                    memory_data = json.load(f)

                self.memory = [MemoryItem.from_dict(item_data)
                               for item_data in memory_data.get("memories", [])]

                self._access_counts = defaultdict(int, memory_data.get("access_counts", {}))
                self._domain_patterns = defaultdict(list, memory_data.get("domain_patterns", {}))
                self._knowledge_lineage = defaultdict(list, memory_data.get("knowledge_lineage", {}))
                self._mission_memory_index = defaultdict(list, memory_data.get("mission_memory_index", {}))
                self._mission_success_patterns = defaultdict(list, memory_data.get("mission_success_patterns", {}))
                self._last_id = memory_data.get("last_id", 0)

                for item in self.memory:
                    self._update_indices(item)

                print(f"Loaded {len(self.memory)} memories from persistent storage")

                # FAISS SYNC: Ensure all loaded memories are in vector database (2026-01-31)
                # This fixes issue where FAISS index is out of sync with persistent memory
                if self.vector_db and len(self.memory) > 0:
                    # Check current FAISS size to avoid duplicate syncing
                    faiss_size = 0
                    try:
                        if hasattr(self.vector_db, '_vector_store') and self.vector_db._vector_store is not None:
                            faiss_size = self.vector_db._vector_store.index.ntotal
                    except:
                        pass

                    # Only sync if FAISS is significantly smaller than memory (threshold: 80%)
                    if faiss_size < len(self.memory) * 0.8:
                        print(f"🔄 FAISS out of sync ({faiss_size} vs {len(self.memory)} memories). Rebuilding index...")
                        synced_count = 0
                        action_count = 0
                        user_count = 0
                        for item in self.memory:
                            try:
                                self.vector_db.add_item(item)
                                synced_count += 1
                                if "[ACTION]" in item.content:
                                    action_count += 1
                                elif "[USER]" in item.content:
                                    user_count += 1
                            except Exception as sync_err:
                                pass  # Skip items that fail to sync
                        print(f"✅ FAISS Sync complete: {synced_count} memories ({user_count} [USER] | {action_count} [ACTION])")
                    else:
                        print(f"✅ FAISS index in sync ({faiss_size} items)")

        except Exception as e:
            print(f"Failed to load persistent memory: {e}")

    def _save_persistent_missions(self):
        """Save mission state to disk"""
        try:
            mission_data = {
                "missions": {mid: mission.to_dict() for mid, mission in self.missions.items()},
                "active_mission_ids": self.active_mission_ids
            }

            os.makedirs("ChatHistory", exist_ok=True)
            with open("ChatHistory/persistent_missions.json", "w", encoding="utf-8") as f:
                json.dump(mission_data, f, indent=2)

        except Exception as e:
            print(f"Failed to save persistent missions: {e}")

    def _load_persistent_missions(self):
        """Load mission state from disk"""
        try:
            if os.path.exists("ChatHistory/persistent_missions.json"):
                with open("ChatHistory/persistent_missions.json", "r", encoding="utf-8") as f:
                    mission_data = json.load(f)

                self.missions = {
                    mid: Mission.from_dict(mdata)
                    for mid, mdata in mission_data.get("missions", {}).items()
                }
                self.active_mission_ids = mission_data.get("active_mission_ids", [])

                # DISABLED: Auto-pause should NOT run on app restart
                # User wants explicit control over mission completion
                # Only pause missions when user explicitly says "mission X is complete"
                # self._auto_pause_inactive_missions()

                print(f"✅ Loaded {len(self.missions)} missions ({len(self.active_mission_ids)} active) - Auto-pause DISABLED")

        except Exception as e:
            print(f"Failed to load persistent missions: {e}")

    def _auto_pause_inactive_missions(self):
        """Automatically pause missions that have been inactive for too long"""
        pause_threshold_days = self.config.config.get("mission_auto_pause_days", 30)
        pause_threshold_seconds = pause_threshold_days * 24 * 3600
        current_time = time.time()

        paused_count = 0
        for mission_id in self.active_mission_ids[:]:  # Copy list to avoid modification during iteration
            mission = self.missions.get(mission_id)
            if mission and (current_time - mission.last_activity_time) > pause_threshold_seconds:
                mission.status = "paused"
                self.active_mission_ids.remove(mission_id)
                paused_count += 1

        if paused_count > 0:
            print(f"Auto-paused {paused_count} inactive missions")

    def _get_active_missions(self) -> List[Mission]:
        """Get list of currently active missions, sorted by priority"""
        active_missions = []
        for mission_id in self.active_mission_ids:
            if mission_id in self.missions:
                active_missions.append(self.missions[mission_id])

        return sorted(active_missions, key=lambda m: m.priority, reverse=True)

    def _assemble_mission_context(self, query: str, max_findings_per_mission: int = None) -> str:
        """
        Dynamically build context that combines mission progress with relevant memories
        This is the core of mission-persistent context
        """
        if max_findings_per_mission is None:
            max_findings_per_mission = self.config.config.get("max_mission_context_findings", 5)

        active_missions = self._get_active_missions()
        print(f"🎯 DEBUG: _assemble_mission_context - {len(active_missions)} active missions")

        if not active_missions:
            print(f"❌ DEBUG: No active missions found")
            return ""

        # Find missions relevant to query
        relevant_missions = []
        for mission in active_missions:
            relevance = mission.is_relevant_to_query(query)
            print(f"🔍 DEBUG: Mission '{mission.title}' relevance: {relevance:.2f}")
            if relevance > self.config.config.get("mission_relevance_threshold", 0.3):
                relevant_missions.append((mission, relevance))

        if not relevant_missions:
            print(f"❌ DEBUG: No relevant missions found for query")
            return ""

        print(f"✅ DEBUG: {len(relevant_missions)} missions are relevant")

        # Sort by relevance and limit to most relevant missions
        relevant_missions.sort(key=lambda x: x[1], reverse=True)
        context_parts = []

        for mission, relevance in relevant_missions[:3]:  # Limit to top 3 relevant missions
            mission_context = [f"🎯 ACTIVE MISSION: {mission.title}"]

            if mission.current_focus:
                mission_context.append(f"Current Focus: {mission.current_focus}")

            # Add key findings, prioritized by importance and recency
            if mission.key_findings:
                recent_findings = sorted(mission.key_findings,
                                         key=lambda f: (f["importance"], f["timestamp"]),
                                         reverse=True)[:max_findings_per_mission]

                if recent_findings:
                    mission_context.append("Key Findings:")
                    for finding in recent_findings:
                        finding["access_count"] += 1  # Track access for future prioritization
                        mission_context.append(f"  • {finding['content']}")

            # Add next steps if query seems action-oriented
            action_keywords = ['what', 'how', 'should', 'next', 'do', 'plan', 'strategy']
            if mission.next_steps and any(kw in query.lower() for kw in action_keywords):
                mission_context.append("Planned Next Steps:")
                for step in mission.next_steps[:3]:  # Limit to first 3 steps
                    mission_context.append(f"  • {step}")

            # Add obstacles if query suggests problem-solving
            problem_keywords = ['problem', 'issue', 'challenge', 'stuck', 'difficult', 'help']
            if mission.obstacles and any(kw in query.lower() for kw in problem_keywords):
                mission_context.append("Known Challenges:")
                for obstacle in mission.obstacles[:2]:  # Limit to first 2 obstacles
                    mission_context.append(f"  • {obstacle}")

            context_parts.append("\n".join(mission_context))

        return "\n\n".join(context_parts)

    def _extract_mission_updates(self, user_input: str, ai_response: str, active_missions: List[Mission]) -> List[
        Dict[str, Any]]:
        """
        Extract potential mission updates from the conversation
        This is how the system learns and updates mission state continuously
        """
        content_to_analyze = user_input  # Only analyze user input
        updates = []

        # Patterns that suggest mission progress or updates
        progress_patterns = [
            (r'\b(completed|finished|done|accomplished)\b', "completion"),
            (r'\b(found|discovered|learned|realized)\b', "finding"),
            (r'\b(problem|issue|obstacle|challenge)\b', "obstacle"),
            (r'\b(works|working|successful|effective)\b', "success"),
            (r'\b(failed|doesn\'t work|unsuccessful)\b', "failure"),
            (r'\b(next|plan|should|will do)\b', "next_step")
        ]

        content_lower = content_to_analyze.lower()

        for mission in active_missions:
            mission_relevance = mission.is_relevant_to_query(content_to_analyze)

            if mission_relevance > 0.3:  # Mission is relevant to this conversation
                for pattern, update_type in progress_patterns:
                    if re.search(pattern, content_lower):
                        updates.append({
                            "mission_id": mission.id,
                            "type": update_type,
                            "content": content_to_analyze,
                            "timestamp": time.time(),
                            "relevance_score": mission_relevance
                        })
                        break  # Only one update type per mission per conversation

        return updates

    def _apply_mission_updates(self, updates: List[Dict[str, Any]]):
        """Apply extracted updates to mission state"""
        for update in updates:
            mission_id = update["mission_id"]
            if mission_id not in self.missions:
                continue

            mission = self.missions[mission_id]
            mission.update_activity()

            update_type = update["type"]
            content = update["content"]

            if update_type == "finding":
                # Extract the specific finding from the content
                finding = self._extract_key_finding(content)
                if finding:
                    mission.add_key_finding(finding, importance=7.0, source="conversation")

            elif update_type == "completion":
                mission.progress_indicators["completion_signals"] = mission.progress_indicators.get(
                    "completion_signals", 0) + 1

                # If multiple completion signals, suggest mission completion
                if mission.progress_indicators.get("completion_signals", 0) >= 3:
                    mission.status = "completed"
                    if mission_id in self.active_mission_ids:
                        self.active_mission_ids.remove(mission_id)

            elif update_type == "obstacle":
                obstacle = self._extract_obstacle(content)
                if obstacle and obstacle not in mission.obstacles:
                    mission.obstacles.append(obstacle)

            elif update_type == "success":
                strategy = self._extract_successful_strategy(content)
                if strategy and strategy not in mission.successful_strategies:
                    mission.successful_strategies.append(strategy)

            elif update_type == "next_step":
                next_step = self._extract_next_step(content)
                if next_step and next_step not in mission.next_steps:
                    mission.next_steps.append(next_step)

    def _extract_key_finding(self, content: str) -> Optional[str]:
        """Extract key finding from conversation content"""
        # Simple extraction - could be enhanced with NLP
        sentences = content.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['found', 'discovered', 'learned', 'realized']):
                return sentence.strip()
        return None

    def _extract_obstacle(self, content: str) -> Optional[str]:
        """Extract obstacle description from conversation content"""
        sentences = content.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['problem', 'issue', 'obstacle', 'challenge']):
                return sentence.strip()
        return None

    def _extract_successful_strategy(self, content: str) -> Optional[str]:
        """Extract successful strategy from conversation content"""
        sentences = content.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['works', 'working', 'successful', 'effective']):
                return sentence.strip()
        return None

    def _extract_next_step(self, content: str) -> Optional[str]:
        """Extract next step from conversation content"""
        sentences = content.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['next', 'plan', 'should', 'will do']):
                return sentence.strip()
        return None

    # Enhanced public interface methods with mission support
    def process_input(self, raw_input: str, active_mission_id: str = None, mode: str = "CHAT_MODE") -> str:
        """
        Enhanced input processing with mission-persistent context
        This is the brain's attention mechanism - it decides what's relevant based on current goals

        Args:
            raw_input: User's input text
            active_mission_id: Optional mission ID for context
            mode: "CHAT_MODE" or "ACTION_MODE" - affects emotion keyword boost (2026-01-22)
        """
        if not raw_input.strip():
            return raw_input

        print(f"🔍 DEBUG: process_input called with: '{raw_input[:50]}...' (mode: {mode})")

        # Get active missions
        if active_mission_id and active_mission_id in self.missions:
            relevant_missions = [self.missions[active_mission_id]]
            print(f"🎯 DEBUG: Using specific mission: {relevant_missions[0].title}")
        else:
            relevant_missions = self._get_active_missions()
            print(f"🎯 DEBUG: Found {len(relevant_missions)} active missions")
            for mission in relevant_missions:
                print(f"  - {mission.title} (ID: {mission.id})")

        # Build mission context
        mission_context = self._assemble_mission_context(raw_input)
        print(f"📋 DEBUG: Mission context length: {len(mission_context)} chars")
        if mission_context:
            print(f"📋 DEBUG: Mission context preview: '{mission_context[:200]}...'")
        else:
            print(f"❌ DEBUG: No mission context generated")

        # Search for relevant memories - Use config value for memories_per_prompt
        # Now includes brain-like boosts: Emotion > Timestamp > Frequency (2026-01-22)
        memories_per_prompt = self.config.config.get("memories_per_prompt", 50)
        relevant_memories = self._semantic_search(raw_input, top_k=memories_per_prompt, include_superseded=False, mode=mode)
        print(f"🧠 DEBUG: Found {len(relevant_memories)} relevant memories (limit: {memories_per_prompt} from config)")
        for i, memory in enumerate(relevant_memories):
            print(f"  Memory {i + 1}: '{memory.content[:100]}...' (missions: {memory.associated_missions})")

        # Also check for identity-related queries
        identity_keywords = ["my name", "who am i", "what do you know about me", "my preferences"]
        if any(keyword in raw_input.lower() for keyword in identity_keywords):
            identity_memories = [m for m in self.memory if "user_identity" in m.tags]
            relevant_memories.extend(identity_memories[:3])

        # Build context with knowledge evolution awareness and mission integration
        context_parts = []

        # Add mission context first - this provides goal-oriented framing
        if mission_context:
            context_parts.append(f"🧠 [MISSION CONTEXT]\n{mission_context}")

        # Add relevant memories with [USER] vs [ACTION] distinction (2026-01-31)
        user_memories = []
        action_memories = []
        memories_limit = self.config.config.get("memories_per_prompt", 10)

        for item in relevant_memories[:memories_limit]:
            self._access_counts[item.id] = self._access_counts.get(item.id, 0) + 1

            # Determine prefix based on type
            if item.supersedes:
                prefix = "🔄 Updated knowledge"
            elif item.metadata.get("tier") == 1:
                prefix = "💎 Core knowledge"
            elif "error_pattern" in item.tags:
                prefix = "⚠️ Known issue"
            elif "success_pattern" in item.tags:
                prefix = "✅ Proven solution"
            else:
                prefix = "📋 Context"

            formatted_memory = f"{prefix}: {item.content}"

            # Split into USER vs ACTION
            if "[ACTION]" in item.content:
                action_memories.append(formatted_memory)
            else:
                user_memories.append(formatted_memory)

        if user_memories or action_memories:
            memory_section_parts = []
            memory_section_parts.append("🧠 [MEMORY CONTEXT]")
            memory_section_parts.append("=" * 60)

            if user_memories:
                memory_section_parts.append("**[USER] MEMORIES** (Conversations with user - preferences/requests):")
                memory_section_parts.extend(user_memories)
                memory_section_parts.append("")

            if action_memories:
                memory_section_parts.append("**[ACTION] MEMORIES** (VERIFIED FACTS from AI agents - Browsing/Computer/Coding/Robot):")
                memory_section_parts.append("NOTE: These are actual discoveries from agent actions, not assumptions.")
                memory_section_parts.extend(action_memories)
                memory_section_parts.append("")

            memory_section_parts.append("=" * 60)
            memory_section = "\n".join(memory_section_parts)
            context_parts.append(memory_section)

        # Build enhanced input
        if context_parts:
            context_join = "\n\n".join(context_parts)
            enhanced = f"""{context_join}

    ---

    💬 CURRENT INPUT:
    {raw_input}

    Please respond using both your knowledge and the relevant context above. Pay special attention to any active mission context to ensure your response helps progress toward the stated goals. If any memory contradicts your response, explain the difference and provide the most accurate information.""".strip()
        else:
            enhanced = raw_input

        return enhanced

    def _is_completion_statement(self, user_input: str) -> bool:
        """Check if the input is about completing/finishing something"""
        completion_keywords = [
            'completed', 'finished', 'done', 'accomplished', 'achieved',
            'complete', 'finish', 'wrap up', 'conclude', 'end'
        ]
        input_lower = user_input.lower()
        return any(keyword in input_lower for keyword in completion_keywords)

    def _get_recent_conversation_context(self) -> List[str]:
        """Get recent conversation for context awareness"""
        try:
            with open("ChatHistory/Last5Interactions.txt", "r", encoding="utf-8") as f:
                content = f.read()
                return content.split('\n\n')[-5:]  # Last 5 interactions
        except FileNotFoundError:
            return []

    def update_memory(self, user_input: str, ai_response: str, active_mission_id: str = None,
                      mode: str = "CHAT_MODE") -> None:
        """
        Enhanced memory update with unified storage for CHAT_MODE and ACTION_MODE
        This is how the brain forms new memories and updates mission progress

        Args:
            user_input: User's input text
            ai_response: AI's response text
            active_mission_id: Optional mission ID for context
            mode: "CHAT_MODE" (USER ↔ AI conversations) or "ACTION_MODE" (SYSTEM ↔ AI automation)
        """
        if not user_input.strip() and not ai_response.strip():
            return

        # Add mode tagging for unified storage with distinction
        if mode == "ACTION_MODE":
            user_input_tagged = f"[ACTION] {user_input}"
        else:
            user_input_tagged = f"[USER] {user_input}"

        # Use tagged input for processing
        user_input = user_input_tagged

        # ═══════════════════════════════════════════════════════════════════
        # FILTERING & SAFEGUARDS - Prevent garbage/duplicate/mode-switch memories
        # ═══════════════════════════════════════════════════════════════════

        # Filter 1: Mode Switch Commands - Skip memory storage for mode switching
        MODE_SWITCH_PATTERNS = [
            r"^(activate|switch\s+to|enable|use)\s+(action|chat)\s+mode$",
            r"^(action|chat)\s+mode$",
            r"^(go\s+to|enter)\s+(action|chat)\s+mode$"
        ]
        user_input_clean = user_input.replace("[ACTION] ", "").replace("[USER] ", "")
        user_input_lower = user_input_clean.lower().strip()
        for pattern in MODE_SWITCH_PATTERNS:
            if re.match(pattern, user_input_lower):
                print(f"⚠️ Skipping memory storage: Mode switch command detected")
                return

        # Filter 2: Garbage Content - Skip DOM fragments, XML, empty content
        GARBAGE_PATTERNS = [
            r'<[^>]{100,}>',  # Long XML/HTML tags
            r'(?:class|id|data-[a-z]+)=["\'][^"\']{50,}["\']',  # Long HTML attributes
            r'^[\s\n\r]*$',  # Empty or whitespace only
            r'^\[ACTION\]\s*$',  # Only mode tag, no content
            r'^\[USER\]\s*$'  # Only mode tag, no content
        ]
        for pattern in GARBAGE_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                print(f"⚠️ Skipping memory storage: Garbage content detected (pattern: {pattern[:30]}...)")
                return

        # Filter 3: Duplicate Detection - Hash-based quick check
        interaction_hash = hashlib.md5(f"{user_input}_{ai_response}".encode()).hexdigest()
        for memory in list(self.memory)[-100:]:  # Check last 100 memories
            existing_hash = hashlib.md5(f"{memory.content}".encode()).hexdigest()
            if interaction_hash == existing_hash:
                print(f"⚠️ Skipping memory storage: Exact duplicate detected (hash match)")
                return

        # Get recent conversation context
        recent_context = self._get_recent_conversation_context()

        # Get CLEAN user input (without mode tags) for mission detection
        # CRITICAL: Mission detection must use ORIGINAL user input without [ACTION]/[USER] tags
        user_input_for_missions = user_input.replace("[ACTION] ", "").replace("[USER] ", "")

        # RE-ENABLED: EXPLICIT MISSION DETECTION ONLY (Confidence >= 0.9)
        # User wants explicit patterns like "our next mission is..." to work
        # But disable low-confidence auto-detection

        # EXPLICIT COMPLETION DETECTION (when user says "mission X is complete")
        # Use CLEAN input without mode tags for accurate pattern matching
        self._check_mission_completion(user_input_for_missions, ai_response)

        # EXPLICIT MISSION DETECTION (only HIGH confidence >= 0.9, e.g., "our next mission is...")
        # User wants ONLY explicit "our next mission is..." patterns (confidence 0.9, not weak 0.6 patterns)
        # Use CLEAN input without mode tags for accurate pattern matching
        if not self._is_completion_statement(user_input_for_missions):
            detected_mission = self._detect_new_mission(user_input_for_missions, recent_context)
            if detected_mission and detected_mission.get("confidence", 0) >= 0.9:  # ONLY strong explicit patterns (is_strong=True)
                mission_id = self.create_mission(
                    title=detected_mission["title"],
                    description=detected_mission.get("description", ""),
                    priority=detected_mission.get("priority", 5),
                    context_keywords=detected_mission.get("keywords", [])
                )
                print(f"✅ EXPLICIT MISSION CREATED (confidence {detected_mission['confidence']:.2f}): {detected_mission['title']} (ID: {mission_id})")
                active_mission_id = mission_id
            elif detected_mission:
                print(f"⚠️ Mission signal too weak for auto-creation (confidence {detected_mission['confidence']:.2f} < 0.9): {detected_mission['title']}")

        # Get active missions for context-aware analysis
        if active_mission_id and active_mission_id in self.missions:
            active_missions = [self.missions[active_mission_id]]
        else:
            active_missions = self._get_active_missions()

        # Combine input and response for complete context
        full_content = f"User: {user_input}\nAI: {ai_response}"

        # ← ADD THESE LINES TO PREVENT DUPLICATE STORAGE
        # Check ALL existing memories for exact duplicates using hash
        content_hash = hashlib.md5(full_content.encode('utf-8')).hexdigest()
        for existing in self.memory:
            existing_hash = hashlib.md5(existing.content.encode('utf-8')).hexdigest()
            if content_hash == existing_hash:
                print(f"⚠️ DUPLICATE BLOCKED: Already stored as {existing.id}")
                return

        # Enhanced importance analysis with mission awareness
        priority_score, special_tags, tier, confidence_score = self._advanced_importance_analysis(
            full_content, context="", active_missions=active_missions
        )

        # Extract semantic tags
        auto_tags = self._extract_tags(full_content)
        all_tags = list(set(special_tags + auto_tags))

        # Determine associated missions
        associated_missions = []
        mission_relevance_scores = {}

        for mission in active_missions:
            relevance = mission.is_relevant_to_query(full_content)
            if relevance > 0.3:  # Significant relevance threshold
                associated_missions.append(mission.id)
                mission_relevance_scores[mission.id] = relevance

        # Create comprehensive metadata
        metadata = {
            "type": self._determine_memory_type(full_content),
            "source": "user_ai_interaction",
            "priority": priority_score,
            "tier": tier,
            "permanent": tier == 1,
            "timestamp": time.time(),
            "access_count": 0,
            "domain": self._detect_domain(full_content),
            "has_mission_context": len(associated_missions) > 0
        }

        # Create memory item with mission associations
        item = MemoryItem(
            id=self._generate_id(),
            content=full_content,
            embedding=self._create_embedding(full_content),
            metadata=metadata,
            timestamp=time.time(),
            tags=all_tags,
            confidence_score=confidence_score,
            associated_missions=associated_missions,
            mission_relevance_scores=mission_relevance_scores
        )

        # Handle knowledge evolution and corrections
        item = self._handle_knowledge_evolution(item)

        # Add to memory systems
        self.memory.append(item)
        self._update_indices(item)

        # Store in vector database
        if self.vector_db:
            try:
                self.vector_db.add_item(item)
            except Exception as e:
                print(f"Vector DB storage error: {e}")

        # Extract and apply mission updates
        if active_missions:
            mission_updates = self._extract_mission_updates(user_input, ai_response, active_missions)
            self._apply_mission_updates(mission_updates)

        # Intelligent pruning
        self._intelligent_pruning()

        # Auto-save periodically
        self._save_counter += 1
        if self._save_counter >= self.config.config.get("auto_save_interval", 10):
            self._save_persistent_memory()
            self._save_persistent_missions()
            self._save_counter = 0

    def _determine_memory_type(self, content: str) -> str:
        """Determine the type of memory based on content analysis"""
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["fix", "bug", "error", "crash", "problem"]):
            return "problem_solving"
        elif any(kw in content_lower for kw in ["code", "function", "programming", "syntax"]):
            return "technical"
        elif any(kw in content_lower for kw in ["my name", "i am", "preference", "like", "age"]):
            return "personal"
        elif any(kw in content_lower for kw in ["explain", "how", "why", "what", "define"]):
            return "educational"
        elif any(kw in content_lower for kw in ["create", "make", "build", "design"]):
            return "creative"
        elif any(kw in content_lower for kw in ["mission", "goal", "objective", "plan", "strategy"]):
            return "mission_related"
        else:
            return "general"

    def _detect_domain(self, content: str) -> str:
        """Detect the domain/field of the content for better organization"""
        content_lower = content.lower()

        domain_keywords = {
            "programming": ["code", "function", "variable", "debug", "compile", "programming"],
            "science": ["research", "experiment", "hypothesis", "data", "analysis"],
            "business": ["strategy", "market", "revenue", "customer", "sales"],
            "health": ["health", "medicine", "doctor", "treatment", "symptoms"],
            "education": ["learn", "study", "teach", "knowledge", "concept"],
            "personal": ["my", "i am", "preference", "family", "hobby"],
            "daily_life": ["shopping", "errands", "routine", "daily", "home"],
            "travel": ["trip", "travel", "visit", "location", "journey"],
            "mission_planning": ["mission", "goal", "objective", "plan", "strategy", "task"]
        }

        for domain, keywords in domain_keywords.items():
            if sum(1 for kw in keywords if kw in content_lower) >= 2:
                return domain

        return "general"

    # Mission management interface methods

    def create_mission(self, title: str, description: str = "", priority: int = 5,
                       relevant_domains: List[str] = None, context_keywords: List[str] = None) -> str:
        """
        Create a new mission and return its ID
        This is like setting a new goal that the brain will maintain awareness of
        """
        mission_id = self._generate_id("mission")

        mission = Mission(
            id=mission_id,
            title=title,
            description=description,
            start_time=time.time(),
            status="active",
            priority=priority,
            relevant_domains=relevant_domains or [],
            context_keywords=context_keywords or []
        )

        self.missions[mission_id] = mission

        # Add to active missions, maintaining priority order
        self.active_mission_ids.append(mission_id)
        self.active_mission_ids.sort(key=lambda mid: self.missions[mid].priority, reverse=True)

        # Limit active missions
        max_active = self.config.config.get("max_active_missions", 5)
        if len(self.active_mission_ids) > max_active:
            # Move lowest priority missions to paused status
            excess_missions = self.active_mission_ids[max_active:]
            for excess_id in excess_missions:
                self.missions[excess_id].status = "paused"
            self.active_mission_ids = self.active_mission_ids[:max_active]

        print(f"Created mission: {title} (ID: {mission_id})")
        return mission_id

    def update_mission(self, mission_id: str, **kwargs) -> bool:
        """Update mission properties"""
        if mission_id not in self.missions:
            return False

        mission = self.missions[mission_id]

        for key, value in kwargs.items():
            if hasattr(mission, key):
                setattr(mission, key, value)

        mission.update_activity()
        return True

    def complete_mission(self, mission_id: str) -> bool:
        """Mark a mission as completed"""
        if mission_id not in self.missions:
            return False

        mission = self.missions[mission_id]
        mission.status = "completed"
        mission.update_activity()

        if mission_id in self.active_mission_ids:
            self.active_mission_ids.remove(mission_id)

        # Store successful patterns for future missions
        if mission.successful_strategies:
            self._mission_success_patterns[mission.title].append({
                "strategies": mission.successful_strategies,
                "completion_time": time.time() - mission.start_time,
                "total_interactions": mission.total_interactions
            })

        print(f"Completed mission: {mission.title}")
        return True

    def pause_mission(self, mission_id: str) -> bool:
        """Pause an active mission"""
        if mission_id not in self.missions:
            return False

        mission = self.missions[mission_id]
        mission.status = "paused"

        if mission_id in self.active_mission_ids:
            self.active_mission_ids.remove(mission_id)

        return True

    def resume_mission(self, mission_id: str) -> bool:
        """Resume a paused mission"""
        if mission_id not in self.missions:
            return False

        mission = self.missions[mission_id]
        mission.status = "active"
        mission.update_activity()

        if mission_id not in self.active_mission_ids:
            self.active_mission_ids.append(mission_id)
            self.active_mission_ids.sort(key=lambda mid: self.missions[mid].priority, reverse=True)

            # Maintain active mission limit
            max_active = self.config.config.get("max_active_missions", 5)
            if len(self.active_mission_ids) > max_active:
                excess_missions = self.active_mission_ids[max_active:]
                for excess_id in excess_missions:
                    self.missions[excess_id].status = "paused"
                self.active_mission_ids = self.active_mission_ids[:max_active]

        return True

    def get_mission_summary(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive mission summary"""
        if mission_id not in self.missions:
            return None

        mission = self.missions[mission_id]

        # Get associated memories
        associated_memory_count = len([m for m in self.memory if mission_id in m.associated_missions])

        return {
            "mission": mission.to_dict(),
            "associated_memories": associated_memory_count,
            "days_active": (time.time() - mission.start_time) / (24 * 3600),
            "days_since_activity": (time.time() - mission.last_activity_time) / (24 * 3600)
        }

    # Enhanced public interface methods

    def get_memory_count(self) -> int:
        """Return current number of stored memories"""
        return len(self.memory)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics with mission information"""
        self._organize_by_tiers()

        active_missions = self._get_active_missions()

        return {
            "total_memories": len(self.memory),
            "tier1_permanent": len(self._tier1_memories),
            "tier2_high_persistence": len(self._tier2_memories),
            "tier3_standard": len(self._tier3_memories),
            "max_configured": self.config.config["max_total_memories"],
            "most_accessed": max(self._access_counts.values()) if self._access_counts else 0,
            "knowledge_chains": len(self._knowledge_lineage),
            "domains_detected": len(self._domain_patterns),
            "total_missions": len(self.missions),
            "active_missions": len(self.active_mission_ids),
            "mission_memory_associations": sum(len(memories) for memories in self._mission_memory_index.values())
        }

    def search_memories(self, query: str, top_k: int = 10, mission_filter: str = None, mode: str = "CHAT_MODE") -> List[Dict[str, Any]]:
        """Search memories with optional mission filtering and brain-like boosts (2026-01-22)"""
        results = self._semantic_search(query, top_k=top_k, include_superseded=False, mission_filter=mission_filter, mode=mode)
        return [item.to_dict() for item in results]

    def get_active_missions_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all active missions"""
        active_missions = self._get_active_missions()
        summaries = []

        for mission in active_missions:
            summary = self.get_mission_summary(mission.id)
            if summary:
                summaries.append(summary)

        return summaries

    def update_max_memories(self, new_max: int):
        """Update maximum memory limit"""
        self.config.update_max_memories(new_max)
        print(f"Updated max memories to {new_max}")

        if len(self.memory) > new_max:
            self._intelligent_pruning()

    def force_save(self):
        """Force save both memory and mission state to disk"""
        self._save_persistent_memory()
        self._save_persistent_missions()

    def clear_all_memories(self):
        """Clear all memories (use with caution!)"""
        self.memory.clear()
        self._tier1_memories.clear()
        self._tier2_memories.clear()
        self._tier3_memories.clear()
        self._tag_index.clear()
        self._id_index.clear()
        self._knowledge_lineage.clear()
        self._mission_memory_index.clear()
        self._access_counts.clear()
        self._save_persistent_memory()

    def clear_all_missions(self):
        """Clear all missions (use with caution!)"""
        self.missions.clear()
        self.active_mission_ids.clear()
        self._mission_memory_index.clear()
        self._mission_success_patterns.clear()
        self._save_persistent_missions()


# Global instance for easy integration - maintains backward compatibility
_global_rag_instance: Optional[AdvancedRAGCore] = None


def get_rag_instance() -> AdvancedRAGCore:
    """Get or create global RAG instance"""
    global _global_rag_instance
    if _global_rag_instance is None:
        try:
            _global_rag_instance = AdvancedRAGCore()
        except Exception as e:
            print(f"Failed to initialize RAG with vector DB: {e}")
            _global_rag_instance = AdvancedRAGCore()
    return _global_rag_instance


# Enhanced global functions that maintain backward compatibility while adding mission support

def process_input(raw_input: str, active_mission_id: str = None, mode: str = "CHAT_MODE") -> str:
    """
    🧠 GLOBAL FUNCTION: Pre-process input with brain-like retrieval boosts (2026-01-22)
    Now includes: Emotion Keywords > Timestamp (Recency) > Frequency (Access Count)

    Args:
        raw_input: User's input text
        active_mission_id: Optional mission ID for context
        mode: "CHAT_MODE" or "ACTION_MODE" - affects emotion keyword boost
    """
    rag = get_rag_instance()
    return rag.process_input(raw_input, active_mission_id, mode)


def update_memory(user_input: str, ai_response: str, active_mission_id: str = None,
                  mode: str = "CHAT_MODE") -> None:
    """
    🧠 GLOBAL FUNCTION: Update memory with unified storage for CHAT_MODE and ACTION_MODE
    Enhanced to support mission context and mode distinction while maintaining backward compatibility

    Args:
        user_input: User's input text
        ai_response: AI's response text
        active_mission_id: Optional mission ID for context
        mode: "CHAT_MODE" (USER ↔ AI) or "ACTION_MODE" (SYSTEM ↔ AI) - Default: "CHAT_MODE"
    """
    rag = get_rag_instance()
    rag.update_memory(user_input, ai_response, active_mission_id, mode)


def get_memory_stats() -> Dict[str, Any]:
    """
    🧠 GLOBAL FUNCTION: Get comprehensive memory and mission statistics
    """
    rag = get_rag_instance()
    return rag.get_memory_stats()


# New mission-specific global functions

def create_mission(title: str, description: str = "", priority: int = 5,
                   relevant_domains: List[str] = None, context_keywords: List[str] = None) -> str:
    """
    🎯 GLOBAL FUNCTION: Create a new mission
    """
    rag = get_rag_instance()
    return rag.create_mission(title, description, priority, relevant_domains, context_keywords)


def complete_mission(mission_id: str) -> bool:
    """
    🎯 GLOBAL FUNCTION: Complete a mission
    """
    rag = get_rag_instance()
    return rag.complete_mission(mission_id)


def pause_mission(mission_id: str) -> bool:
    """
    🎯 GLOBAL FUNCTION: Pause a mission
    """
    rag = get_rag_instance()
    return rag.pause_mission(mission_id)


def resume_mission(mission_id: str) -> bool:
    """
    🎯 GLOBAL FUNCTION: Resume a paused mission
    """
    rag = get_rag_instance()
    return rag.resume_mission(mission_id)


def get_active_missions() -> List[Dict[str, Any]]:
    """
    🎯 GLOBAL FUNCTION: Get all active missions summary
    """
    rag = get_rag_instance()
    return rag.get_active_missions_summary()


def get_mission_summary(mission_id: str) -> Optional[Dict[str, Any]]:
    """
    🎯 GLOBAL FUNCTION: Get detailed mission summary
    """
    rag = get_rag_instance()
    return rag.get_mission_summary(mission_id)


# Maintain all existing global functions for backward compatibility

def update_max_memories_global(new_max: int):
    """🧠 GLOBAL FUNCTION: Update memory limit from GUI"""
    rag = get_rag_instance()
    rag.update_max_memories(new_max)


def search_memories_global(query: str, top_k: int = 10, mission_filter: str = None, mode: str = "CHAT_MODE") -> List[Dict[str, Any]]:
    """🧠 GLOBAL FUNCTION: Search memories with brain-like boosts (2026-01-22)"""
    rag = get_rag_instance()
    return rag.search_memories(query, top_k, mission_filter, mode)


def force_save_global():
    """🧠 GLOBAL FUNCTION: Force save memory and mission state"""
    rag = get_rag_instance()
    rag.force_save()


# Testing and demonstration
if __name__ == "__main__":
    print("🧠 Testing Enhanced RAG Core with Mission-Persistent Context")
    print("=" * 70)

    # Test mission-aware memory system
    test_scenarios = [
        # Personal information
        ("My name is Alex and I'm working on my thesis about AI consciousness",
         "Nice to meet you, Alex! AI consciousness is a fascinating topic for a thesis."),

        # Create a mission
        ("I'm starting research for my thesis on AI consciousness. This is my main project for the next 6 months.",
         "That sounds like an exciting and important research project! I'll help you throughout your thesis work."),

        # Mission-related progress
        ("I found a great paper by David Chalmers on the hard problem of consciousness",
         "Excellent find! Chalmers' work on the hard problem is foundational to consciousness studies."),

        # Unrelated but important personal info
        ("Remember that I prefer coffee over tea, always",
         "Got it! I'll remember your coffee preference."),

        # Back to mission context
        ("What are the main theories of consciousness I should cover in my thesis?",
         "For your thesis, you should cover integrated information theory, global workspace theory, and higher-order thought theories..."),

        # Mission progress
        ("I've completed the literature review section of my thesis",
         "Congratulations on completing the literature review! That's a major milestone."),

        # Test cross-session continuity
        ("What's my name again and what am I working on?",
         "Your name is Alex, and you're working on your thesis about AI consciousness. You've already completed your literature review!")
    ]

    print("Testing mission-persistent memory formation and retrieval...\n")

    # Create a thesis research mission
    mission_id = create_mission(
        title="AI Consciousness Thesis Research",
        description="6-month research project on AI consciousness for thesis",
        priority=9,
        relevant_domains=["education", "science", "research"],
        context_keywords=["consciousness", "AI", "thesis", "research", "philosophy"]
    )

    for i, (user_msg, ai_resp) in enumerate(test_scenarios, 1):
        print(f"Test {i}:")
        print(f"User: {user_msg}")

        # Pre-process input with mission context
        enhanced = process_input(user_msg, mission_id if i > 2 else None)  # Add mission context after mission creation

        # Show enhanced context (truncated for readability)
        if len(enhanced) > len(user_msg) + 50:
            print(f"Enhanced with context: YES ({len(enhanced) - len(user_msg)} chars added)")
        else:
            print(f"Enhanced with context: NO")

        # Update memory with mission context
        update_memory(user_msg, ai_resp, mission_id if i > 2 else None)

        print(f"AI: {ai_resp}")

        # Show current stats
        stats = get_memory_stats()
        print(f"Memory: {stats['total_memories']} total, {stats['active_missions']} active missions")
        print("-" * 50)

    # Test mission completion
    complete_mission(mission_id)

    print("\n🎯 Mission completed! Final system state:")
    final_stats = get_memory_stats()
    print(f"✅ Total memories: {final_stats['total_memories']}")
    print(f"✅ Mission-associated memories: {final_stats['mission_memory_associations']}")
    print(f"✅ Active missions: {final_stats['active_missions']}")
    print(f"✅ Knowledge evolution chains: {final_stats['knowledge_chains']}")

    print("\n🎉 Enhanced RAG system with mission-persistent context is ready!")
    print("Key features demonstrated:")
    print("✅ Mission-persistent context that lasts beyond conversation windows")
    print("✅ Goal-oriented memory importance analysis")
    print("✅ Automatic mission progress tracking")
    print("✅ Cross-session mission and memory continuity")
    print("✅ Backward compatibility with existing RAG functions")
    print("✅ Universal applicability from daily tasks to complex research")

