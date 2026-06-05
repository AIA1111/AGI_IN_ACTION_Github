# AGI IN ACTION - Complete Project Reference

**Last Updated**: 2026-03-01
**Version**: v3.5+ (HEART_BEAT Watchdog + OpenClaw + Vision RAG + ComputerAgent)
**Platform**: M3 Ultra (macOS) - All services local
**Main File**: `AGI IN ACTION(BASIC) 2.3.py` (10,591 lines, ~504KB)

---

## CORE MISSION

A **100% autonomous, self-evolving digital brain** — personal JARVIS-like AI system designed to:
- Run continuously without human intervention
- Learn and grow forever via TEXT + VISION RAG memories (future: LoRA training)
- Operate across 3 platforms: Desktop (2D screen) + Android (mobile) + Humanoid Robot (3D world, future)
- Proactively contact user and perform tasks autonomously

**The "Digital Brain" is NOT the AI model** — it is a unified vector database (or set of databases) containing semantic signatures of TEXT and VISION memories. The brain is model-agnostic and grows forever.

### 6 Core Concepts
1. **Proactive Learning** — Self-directed learning during user inactivity (web browsing, self-chat, RAG/LoRA updates)
2. **Reactive Learning** — Learning from direct user interactions
3. **Proactive Response** — Timer-based proactive outreach to user
4. **Reactive Response** — Standard prompt/response (highest priority, pauses all background work)
5. **Active Mission Tracker** — JSON-based task decomposition into sub-tasks for long-running agents
6. **Emergency Loop Breaker** — Rolling 3-window monitoring to detect/break AI repetition patterns

### 5 Critical Components of Each AI Agent
1. **Asynchronous Timer** — Dedicated timer + JSON file per agent for independent operation
2. **Task Breaker** — Convert complex tasks into numbered sub-tasks in JSON
3. **Loop Breaker** — Monitor last 3 replies for >10% token repetition, trigger wake-up prompt
4. **Rolling Window Context** — Save last 3-5 prompts/replies, feed in every prompt
5. **Infinite RAG Memory** — 5-10 relevant TEXT + VISION memories retrieved/updated per interaction

### Success Criteria
1. **Infinite Memory** — Perfect recall with growing knowledge, learning from past mistakes
2. **No Infinite Loops** — 24/7 autonomous operation without diverging patterns

---

## CURRENT ARCHITECTURE

```
M3 Ultra (Local - All Services Fast)
├── Desktop GUI (10 tabs) - AGI IN ACTION(BASIC) 2.3.py (10,591 lines)
│   ├── Chat: Main conversation interface (CHAT_MODE + ACTION_MODE)
│   ├── Login: Model selection, API config, browser settings, FRP/Nginx/API status
│   ├── Digital Brain: RAG settings, memory management, TEXT RAG boost
│   ├── Whisper STT: Speech-to-text testing interface
│   ├── Kokoro TTS: Text-to-speech generation & playback (10 voices)
│   ├── WebSocket Server: TTS/STT server status monitoring
│   ├── AgentList: Scheduled browser automation (create, schedule, monitor agents)
│   ├── ScreenRecording: Vision recording for Vision RAG
│   ├── ComputerAgent: Autonomous computer control (screen-based agent)
│   └── OpenClaw: OpenClaw integration for ACTION_MODE (conditional, if bridge available)
│
├── Nginx (Port 443) - Entry point for Android via FRP tunnel
├── API Server (Port 8081) - Flask + Waitress
├── LM Studio (Port 1234) - Local LLM (Gemma 3 27B / Qwen 3 VL 30B)
├── WebSocket Server (Port 8765) - Integrated TTS/STT
├── HTTP Audio Server (Port 8766) - Audio file downloads
├── FRP Client → Windows VPS (167.86.108.131) → Android App
│
├── HEART_BEAT Watchdog - Auto-recovery daemon (monitors all services)
│   └── macOS launchd - Survives M3 Ultra reboots automatically
│
└── OpenClaw Gateway (Port 18789) - Alternative ACTION_MODE engine (optional)
```

### Two Operating Modes

**CHAT_MODE** (Conversational):
- Multi-provider support: OpenAI, Anthropic, Google, Groq, Together.ai, x.ai, LM Studio
- Vision support (image + text)
- Streaming (Desktop SSE + Android SSE with sentence-boundary chunking)
- RAG memory: `ChatHistory/persistent_memory.json` tagged [USER]
- Rolling window context for conversation continuity

**ACTION_MODE** (Browser Automation):
- Custom `browser_use` library (heavily modified - NOT standard pip version)
- Chrome + Edge support (macOS/Windows/Linux)
- RAG memory: Same file tagged [ACTION]
- Loop detection (`InfiniteLoopBreaker.py`), DOM timeout recovery
- Human-in-the-loop (HITL) capabilities
- Alternative engines: OpenClaw, ComputerAgent

---

## KEY FOLDERS

### Memory & Configuration

| Folder/File | Purpose |
|---|---|
| `ChatHistory/` | RAG memory storage (CRITICAL) |
| `ChatHistory/persistent_memory.json` (644KB) | Unified TEXT RAG memories (both modes, tagged [USER]/[ACTION]) |
| `ChatHistory/persistent_missions.json` | Active mission tracking |
| `ChatHistory/temporal_data.json` | Time-based events/reminders |
| `ChatHistory/ChatHistory.txt` | Rolling window context (MUST preserve) |
| `ChatHistory/ContextMemory.txt` | Rolling window context (MUST preserve) |
| `faiss_index/` | FAISS vector store for TEXT RAG (CRITICAL) |
| `memory_config.json` (root) | Master RAG configuration |
| `ChatModelList/` | Encrypted API keys + model names for all providers |
| `BrowsingAgent_Config/` | Browser automation settings, RAG settings, TTS config, auth key |
| `BrowserSettings/` | Chrome/Edge browser paths and settings |
| `GeneralSettings/` | App-wide preferences, model switching settings |

### Vision RAG System

| Folder/File | Purpose |
|---|---|
| `Vision_RAG/` | Complete Vision RAG module |
| `Vision_RAG/vision_memories.json` (27MB) | Vision RAG memories (CRITICAL) |
| `Vision_RAG/vision_ragcore_activememory.py` | Active memory layer for vision |
| `Vision_RAG/vision_ragcore.py` | Base Vision RAG engine |
| `Vision_RAG/vision_rag_helpers.py` | Helper functions (memory tags, identity images) |
| `Vision_RAG/vision_memory_config.json` | Vision RAG configuration |
| `Vision_RAG/faiss_index/` | FAISS vector store for Vision RAG |
| `Vision_RAG/clip-vit-large-patch14/` | CLIP model for vision embeddings |
| `Vision_RAG/Identity_Faces/` | Face identity reference images |

### Agent & Automation

| Folder/File | Purpose |
|---|---|
| `browser_use/` | Custom browser automation library (CRITICAL - NOT standard pip!) |
| `Computer_Agent/` | Screen-based autonomous computer control agent |
| `Computer_Agent/gui_integration.py` | ComputerAgent tab GUI + event handling |
| `Computer_Agent/computer_agent_controller.py` | Core agent controller |
| `Computer_Agent/perception/` | Screen perception (OCR, spatial analysis) |
| `Computer_Agent/mission/` | Mission management for computer tasks |
| `Computer_Agent/execution/` | Action execution layer |
| `OpenClaw/` | OpenClaw integration (alternative ACTION_MODE engine) |
| `OpenClaw/openclaw_bridge.py` | Bridge module (tab layout, events, task execution, autostart) |
| `OpenClaw/openclaw_bridge_config.json` | Config: enabled, autostart, timeout |
| `OpenClaw/openclaw-main/` | Full OpenClaw source code |
| `AgentListTab/` | Scheduled browser automation system |
| `AgentListTab/agent_list.py` (80KB) | AgentSystem + AgentScheduler classes |
| `AgentListTab/AgentList/` | Agent task files (Agent 1.txt, etc.) |
| `AgentListTab/AgentConfig/` | Scheduling configs (one-time or repeat) |
| `AgentListTab/WorkReports/` | JSON execution results |
| `InfiniteAgentMemory/` | ACTION_MODE mission tracking (active/ + archive/) |
| `ACTION_MODE_MOBILE/` | Android work reports (current_response.json) |
| `FileManager/` | Browser agent file operations (Uploads/, Downloads/, Common/) |

### HEART_BEAT Watchdog System

| Folder/File | Purpose |
|---|---|
| `HEART_BEAT/` | Auto-recovery daemon for all services |
| `HEART_BEAT/heartbeat_watchdog.py` | Standalone daemon (checks every 60s, max 3 restarts/10min) |
| `HEART_BEAT/service_monitor.py` | Service definitions: Main App, API, Nginx, TTS/STT, OpenClaw, FRP |
| `HEART_BEAT/heartbeat_manager.py` | GUI facade for watchdog |
| `HEART_BEAT/com.agiiinaction.heartbeat.plist` | macOS launchd job (survives reboots) |
| `HEART_BEAT/START_HEARTBEAT.command` | Double-click to install launchd + start watchdog |
| `HEART_BEAT/KILL_HEARTBEAT.command` | Double-click to stop watchdog + uninstall launchd + kill services |
| `HEART_BEAT/watchdog_agi.pid` | PID file for singleton enforcement |

**Monitored Services**: Main App, API Server (8081), Nginx (443, monitor-only), WebSocket TTS (8765), Whisper STT (8766), OpenClaw Gateway (18789), FRP Client
**Survival Chain**: M3 reboots → launchd starts watchdog → watchdog starts Main App → Main App starts child services

### Screen Recording

| Folder/File | Purpose |
|---|---|
| `ScreenRecording/` | Vision recording for Vision RAG |
| `ScreenRecording/screen_recording.py` | VisionRecordingModule (continuous recording + Vision RAG worker) |
| `ScreenRecording/ScreenRecordingSettings.json` | Config (continuous_mode, auto_vision_update) |
| `ScreenRecording/screen_recording_data/` | Captured screenshots |

### TTS/STT

| Folder/File | Purpose |
|---|---|
| `TTS_STT_Project/` | TTS/STT models + original standalone server (archived) |
| `TTS_STT_Project/models/whisper-large-v3/` | Whisper STT model |
| `TTS_STT_Project/models/kokoro-82m/` | Kokoro TTS model (10 voices) |
| `WebSocketClient_TTSAndSTT_5.py` | TTS/STT WebSocket client (used by main app) |
| `WebSocketServer_TTSAndSTT_5.py` | Original standalone server (now integrated in main app) |

### Android Integration

| Folder/File | Purpose |
|---|---|
| `Android/` | Android app source (Kotlin, reference only) |
| `Central AI Memory Local/` | Android ↔ Desktop sync files |
| `nginx/` | Custom reverse proxy (extended timeouts, CRITICAL for Android) |

### Infrastructure

| Folder/File | Purpose |
|---|---|
| `nginx/` | Custom nginx with 120s+ timeouts (DO NOT replace with standard) |
| `venv/` | Python 3.11 virtual environment |
| `backups/` | Important file backups (browser_use, nginx, FRP configs) |
| `Archive/` | Deprecated files (old code, unused modules) |
| `docs/` | All documentation |
| `Testing/` | Experimental code |
| `Requirements/` | Pip freeze snapshots |
| `MasterAgent/` | Empty (placeholder for future Twin Agent System) |

---

## MEMORY SYSTEM (MOST CRITICAL)

### Unified 2-Module TEXT RAG Architecture

```
ragcore_vector_activememory2.py (Active Memory Layer - 1959 lines) ← MAIN ENTRY POINT
├── Global Functions (import from main GUI):
│   ├── process_input(raw_input, active_mission_id) → Before AI call
│   ├── update_memory(user_input, ai_response, active_mission_id, mode) → After AI call
│   ├── get_memory_stats() → Memory statistics
│   └── get_rag_instance() → RAG instance access
├── Enhanced Features:
│   ├── Signal detection (mission/completion analysis)
│   ├── Temporal intelligence (events, reminders)
│   ├── Duplicate prevention (interaction hashing)
│   └── Auto-detection DISABLED (user wants explicit control)
└── Wraps Base Layer ↓

ragcore_vector2.py (Base RAG - 2274 lines)
├── Unified Storage:
│   ├── File: ChatHistory/persistent_memory.json (10,000 limit)
│   ├── FAISS: faiss_index/index.faiss + index.pkl
│   ├── Mode Tagging: [USER] for CHAT_MODE, [ACTION] for ACTION_MODE
│   └── Single storage for both modes (no separation)
├── Filtering & Safeguards:
│   ├── Mode switch command filter
│   ├── Garbage content filter (DOM, XML, empty)
│   └── Duplicate detection (hash-based)
└── Three-tier memory: Permanent / High-Priority / Standard
```

### Vision RAG Architecture
```
Vision_RAG/vision_ragcore_activememory.py (Active Layer)
├── Functions: get_vision_memory_stats, update_vision_rag_memories, process_vision_rag_input
└── Wraps ↓

Vision_RAG/vision_ragcore.py (Base Vision RAG)
├── Storage: Vision_RAG/vision_memories.json (27MB)
├── FAISS: Vision_RAG/faiss_index/
├── Embeddings: CLIP ViT-Large-Patch14
└── Cross-modal: TEXT ↔ VISION memory retrieval
```

### Memory Update Flow (Important!)
- `process_chat_interaction()` → saves chat history + updates context memory + updates lifetime memory
- `update_memory()` → updates RAG vector store ONLY
- **Both must be called** after each AI response (historical bug: some paths only called one)

### Configuration
- **Master config**: `memory_config.json` (root)
- **RAG settings**: `BrowsingAgent_Config/rag_settings.json`
- **Vision config**: `Vision_RAG/vision_memory_config.json`
- Max TEXT memories: 10,000,000 (10M limit)
- Tier percentages: 30% Permanent / 50% High-Priority / 20% Standard

---

## KEY FILES (Root Level)

### Main Application
| File | Size | Purpose |
|---|---|---|
| `AGI IN ACTION(BASIC) 2.3.py` | 504KB, 10,591 lines | Main GUI, 10 tabs, all core logic |

### Core Modules
| File | Size | Purpose |
|---|---|---|
| `ragcore_vector2.py` | 132KB | Base RAG with unified storage |
| `ragcore_vector_activememory2.py` | 90KB | Active memory layer (MAIN RAG ENTRY POINT) |
| `BrowserAgentModule22.py` | 106KB | Browser automation engine |
| `InfiniteLoopBreaker.py` | 97KB | Loop detection + DOM monitoring |
| `FileManager.py` | 55KB | File operations + monitoring |
| `qr_api_linux_module_1.py` | 51KB | QR code generation + Nginx/API server management |
| `WebSocketServer_TTSAndSTT_5.py` | 50KB | Standalone TTS/STT server (archived, now integrated) |
| `WebSocketClient_TTSAndSTT_5.py` | 40KB | TTS/STT WebSocket client |
| `qr_sftp_linux_module_1.py` | 55KB | Deprecated SFTP sync |
| `license_manager_enhanced5.py` | 27KB | Disabled (not used on M3) |
| `dynamic_model_selection.py` | 16KB | Dynamic model switching logic |
| `platform_utils.py` | 7KB | Cross-platform OS detection |
| `cleanup_duplicates.py` | - | RAG duplicate cleanup utility |

### External Module Imports in Main App
```python
# Always available
import BrowserAgentModule22 as browser_module
from BrowserAgentModule22 import force_close_browsers
from agent_list import AgentSystem, AgentScheduler, format_scheduled_agents_display
from Computer_Agent.gui_integration import create_computeragent_tab_layout, handle_computeragent_events

# Conditional (graceful fallback if unavailable)
from OpenClaw.openclaw_bridge import (create_openclaw_tab_layout, handle_openclaw_events,
    execute_openclaw_task, is_gateway_running, autostart_openclaw_services)
from ScreenRecording.screen_recording import VisionRecordingModule
from Vision_RAG.vision_ragcore_activememory import (get_vision_memory_stats,
    force_save_vision_memories, update_vision_rag_memories, process_vision_rag_input)
from Vision_RAG.vision_rag_helpers import (determine_vision_memory_tag, get_identity_image)
```

---

## MAIN APP STRUCTURE (Line Map)

```
Lines 1-200:        Imports, logging setup, conditional module loading
Lines 201-860:      TTS/STT server functions (integrated from WebSocketServer)
Lines 860-1050:     WebSocket server control, HTTP server, cleanup scheduler
Lines 1050-1900:    Agent scheduling, configuration utilities
Lines 1900-2220:    send_message_async(), process_message_thread() (core chat flow)
Lines 2220-2270:    get_system_prompt()
Lines 2270-2430:    prepare_chat_prompt() (RAG context assembly)
Lines 2430-2660:    AI provider functions (OpenAI, Google, Anthropic, LM Studio, etc.)
Lines 2660-2970:    class ModelManager (API key encryption, model storage)
Lines 2970-3140:    class MemoryManager (chat history, context memory)
Lines 3140-4350:    class SFTPManager (deprecated SFTP sync)
Lines 4350-6330:    class UnifiedSystem (Flask routes, mode switching, browser automation)
Lines 6330-6470:    create_login_layout()
Lines 6470-6660:    create_chat_layout()
Lines 6660-6860:    create_digital_brain_layout()
Lines 6860-6950:    create_stt_tab_layout(), create_tts_tab_layout()
Lines 6950-7020:    create_ws_server_tab_layout()
Lines 7020-7110:    create_agentlist_tab_layout()
Lines 7110-7210:    create_screenrecording_tab_layout()
Lines 7210-7350:    create_main_layout(), create_window() (10 tabs assembled here)
Lines 7350-7990:    main() function - startup sequence (services init)
Lines 7990-10570:   Main event loop (all GUI event handlers)
Lines 10570-10591:  Entry point (__name__ == '__main__')
```

### Startup Sequence (inside main(), line 7354)
1. Platform detection (Darwin/Windows/Linux)
2. Log cleanup + browser cleanup
3. ModelManager init + auth key setup
4. Window creation (10 tabs)
5. Folder initialization + settings loading
6. ScreenRecording/Vision module init (auto-start if configured)
7. VPS/API config loading
8. UnifiedSystem init
9. AgentList system init (AgentSystem + AgentScheduler)
10. Nginx + API server start (`qr_api_linux_module_1.start_both_servers()`)
11. WebSocket TTS/STT server start (Whisper + Kokoro model loading)
12. WebSocket client auto-connect
13. Browser module init
14. RAG settings loading
15. Scheduled agents restoration from config files
16. OpenClaw autostart (if available and configured)
17. Main event loop start (1-second timeout polling)

---

## ANDROID CONNECTIVITY

```
Android App → HTTPS (443) → Windows VPS (167.86.108.131) → FRP tunnel → M3 Ultra Nginx (443) → API Server (8081)
```

**Key endpoints:**
- `/chat` (POST) — Blocking chat (CHAT_MODE + ACTION_MODE)
- `/chat/stream` (POST) — SSE streaming chat (CHAT_MODE only)
- WebSocket (8765) — TTS/STT audio

**Android app features:** SSE streaming, Kokoro TTS + Whisper STT, continuous voice mode, ACTION_MODE browser tasks

---

## CRITICAL WARNINGS

### DO NOT Touch These:
1. **`browser_use/`** — Custom library, NOT standard pip version
2. **`nginx/`** — Custom extended timeouts, NOT standard nginx
3. **`ChatHistory/persistent_memory.json`** — TEXT RAG memories
4. **`Vision_RAG/vision_memories.json`** — Vision RAG memories
5. **`faiss_index/`** — TEXT RAG FAISS vector store
6. **`Vision_RAG/faiss_index/`** — Vision RAG FAISS vector store
7. **`ChatHistory/ChatHistory.txt`** — Rolling window context
8. **`ChatHistory/ContextMemory.txt`** — Rolling window context
9. **`ChatHistory/persistent_missions.json`** — Active mission data
10. **`ChatHistory/temporal_data.json`** — Temporal intelligence data

### Known Issues:
1. Desktop → Android sync broken (only Android → Desktop works)
2. Some old Windows paths may exist (low priority)
3. Google.com as default page may trigger captchas
4. HEART_BEAT watchdog cannot restart nginx (requires sudo, not available from launchd daemon) — monitor-only for nginx

### Before Making Changes:
1. Verify current code behavior first
2. Check if feature already exists
3. Document what you're changing and why
4. Test after each change — ripple effects are common in this interconnected codebase
5. Never break working code
6. Move deprecated files to Archive/ (never delete)
7. Important backups go to backups/

---

## 3 CORE COMPONENTS (Current + Future)

1. **Desktop App** (THIS PROJECT) — Central server, all AI models, RAG memory, TTS/STT, agents, browser automation
2. **Android App** — Remote access via FRP tunnel, streaming chat, voice, ACTION_MODE commands
3. **Humanoid Robot** (FUTURE) — Shares same memory system, Desktop acts as planner, robot acts as executor. Being developed separately in MuJoCo simulator.

---

## VERSION HISTORY (Condensed)

| Version | Date | Key Change |
|---|---|---|
| v2.3 | - | Multi-provider support, enhanced memory tiers |
| v3.0 | 2025-10 | macOS migration + Desktop streaming |
| v3.1 | 2025-10 | Android SSE streaming |
| v3.2 | 2025-10 | ACTION_MODE M3 migration |
| v3.3 | 2025-10 | Whisper STT + Voice Persistence + VPS Migration + WebSocket Integration |
| v3.4 | 2025-12 | ACTION_MODE RAG isolation (later unified back to single storage) |
| v3.4.1-4 | 2025-12 | DOM recovery, config persistence, bug fixes |
| v3.4.5 | 2025-12 | AgentList Tab — scheduled browser automation |
| v3.5 | 2026-01 | ComputerAgent tab, scheduled agents restore on startup |
| v3.5+ | 2026-02 | OpenClaw tab, HEART_BEAT watchdog, launchd auto-start, system prompt fix, PySimpleGUI upgrade |

---

## FUTURE INTEGRATION PLANS

1. **Continuous LoRA Training** — Digital Brain project merge (replace LM Studio)
2. **Better Computer Agent** — Enhanced screen-based autonomous control
3. **InfiniteLoopBreaker Improvements** — More robust loop detection
4. **Desktop → Android Sync** — Bidirectional sync restoration
5. **Humanoid Robot Integration** — 3D world actions via MuJoCo simulation
6. **Vision RAG Enhancement** — Cross-modal TEXT ↔ VISION retrieval improvements

---

**Remember**: 90% of code written by Claude across sessions. User doesn't remember all details. Always verify before changing. Never break working code. Never deviate from CORE MISSION.

**Detailed session logs**: See `LAST_SESSION.md` and `ACTIVE_SESSION.md` for per-session change details.
**Core philosophy**: See `Core coding principles and goal.txt` and `CORE CONCEPTS AND COMPONENTS.md` for foundational vision.
