 ---
  Summary of My Understanding

  🎯 Core Vision: Building AGI (Autonomous General Intelligence)

  Your project aims to create a 100% autonomous, self-evolving digital brain modeled after JARVIS from Iron Man, consisting of:

  1. Desktop App (M3 Ultra) - Central server for 2D computer screen automation
  2. Android App - Remote commands/monitoring
  3. Humanoid Robot (future) - 3D physical world actions

  The "Brain" is NOT the AI model - it's the unified vector database (TEXT + VISION RAG memories) that grows forever and can work with any AI model.

  ---
  📐 6 Core Concepts

  1. Proactive Learning - Self-chat, web browsing, RAG/LORA training during user inactivity
  2. Reactive Learning - Learning during direct user interactions
  3. Proactive Response - Timer-based proactive contact (like text messages)
  4. Reactive Response - Standard user prompts (highest priority)
  5. Active Mission Tracker - JSON-based task decomposition into sub-tasks
  6. Emergency Loop Breaker - Rolling 3-window context monitoring to detect/break infinite loops

  ---
  📊 Current Architecture

  M3 Ultra (Local)
  ├── Main GUI (10 tabs): Chat, Login, Digital Brain, Whisper STT, Kokoro TTS,
  │                       WebSocket Server, AgentList, ScreenRecording,
  │                       ComputerAgent, OpenClaw
  ├── Nginx (443) → FRP → Android
  ├── API Server (8081)
  ├── LM Studio (1234) - Gemma 3 27B / Qwen 3 VL 30B
  ├── WebSocket TTS/STT (8765)
  ├── Vision RAG + TEXT RAG memories
  ├── HEART_BEAT Watchdog - Auto-recovery daemon (monitors all services, survives reboots via launchd)
  └── OpenClaw Gateway (18789) - Alternative ACTION_MODE engine

  Two Modes:
  - CHAT_MODE - Conversational AI with multi-provider support
  - ACTION_MODE - Browser automation (browser_use, ComputerAgent, or OpenClaw)


  DO NOT TOUCH:
  - browser_use/ - Custom modified library (not standard pip version)
  - nginx/ - Custom extended timeouts
  - RAG memory files - Sacred, never break
  - FAISS indexes - Core of digital brain
  - Rolling window context - Essential for continuity

  Project Complexity:
  - Merged from multiple independent projects
  - Duplicate code paths exist
  - Can't apply isolated patches - need to understand full flow
  - Connection points between components are critical

  ---
  📁 Key Documentation Files
  ┌──────────────────────────────────────────┬──────────────────────────┐
  │                   File                   │         Purpose          │
  ├──────────────────────────────────────────┼──────────────────────────┤
  │ Core coding principles and goal.txt      │ Core philosophy          │
  ├──────────────────────────────────────────┼──────────────────────────┤
  │ CORE CONCEPTS AND COMPONENTS.md          │ Latest architecture      │